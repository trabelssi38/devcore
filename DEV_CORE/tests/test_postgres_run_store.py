"""Offline contracts for the PostgreSQL durable-run adapter."""

from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
import sys

import pytest

from devcore_engine.runs.postgres_store import PostgresRunStore, _record
from devcore_engine.runs import DurableRunEngine, EffectAlreadyInProgressError, PostgresEffectIdempotencyStore

API_DIR = Path(__file__).resolve().parents[1] / "API"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


class RecordingCursor:
    def __init__(self):
        self.statements = []

    def execute(self, statement, params=()):
        self.statements.append((statement, params))


class RecordingConnection:
    def __init__(self):
        self.cursor_value = RecordingCursor()
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_transaction_sets_project_local_to_transaction_and_closes(monkeypatch):
    store = PostgresRunStore("postgresql://app:unused@127.0.0.1/fixture")
    conn = RecordingConnection()
    monkeypatch.setattr(store, "_connect", lambda: conn)
    with store._transaction("alpha") as cursor:
        cursor.execute("SELECT 1")
    assert conn.cursor_value.statements[0] == (
        "SELECT set_config('app.current_project_id', %s, true)", ("alpha",))
    assert conn.committed and conn.closed and not conn.rolled_back


def test_transaction_rolls_back_and_rejects_unscoped_project(monkeypatch):
    store = PostgresRunStore("postgresql://app:unused@127.0.0.1/fixture")
    conn = RecordingConnection()
    monkeypatch.setattr(store, "_connect", lambda: conn)
    with pytest.raises(RuntimeError):
        with store._transaction("alpha"):
            raise RuntimeError("fixture")
    assert conn.rolled_back and conn.closed and not conn.committed
    with pytest.raises(ValueError):
        with store._transaction("../other"):
            pass


def test_historical_run_projection_has_no_executable_command():
    now = datetime.now(UTC)
    historical = _record({"id": "historical", "project_id": "alpha", "status": "succeeded",
                          "command": None, "metadata": {}, "created_at": now, "updated_at": now})
    assert historical.command == []
    assert historical.project_id == "alpha"


def test_run_store_rejects_remote_database():
    with pytest.raises(ValueError):
        PostgresRunStore("postgresql://app:secret@203.0.113.5/fixture")


def test_durable_migration_forces_rls_on_runs():
    migration = (Path(__file__).resolve().parents[1] / "devcore_engine" / "persistence"
                 / "migrations" / "20261016_durable_runs.sql").read_text(encoding="utf-8")
    assert "ALTER TABLE runs FORCE ROW LEVEL SECURITY" in migration


@pytest.mark.parametrize("team_variable", ["DEVCORE_TASK_READ_MODE", "DEVCORE_IDENTITY_READ_MODE"])
def test_engine_uses_postgres_without_creating_sqlite(monkeypatch, tmp_path, team_variable):
    monkeypatch.setenv(team_variable, "postgres")
    monkeypatch.setenv("DEVCORE_DATABASE_URL", "postgresql://app:unused@127.0.0.1/fixture")
    monkeypatch.delenv("DEVCORE_RUN_STORE", raising=False)
    engine = DurableRunEngine(local_root=tmp_path)
    assert isinstance(engine.store, PostgresRunStore)
    assert isinstance(engine.effects, PostgresEffectIdempotencyStore)
    assert not list(tmp_path.rglob("*.db"))


def test_engine_refuses_sqlite_or_missing_dsn_in_team_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("DEVCORE_TASK_READ_MODE", "postgres")
    monkeypatch.delenv("DEVCORE_DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DEVCORE_DATABASE_URL"):
        DurableRunEngine(local_root=tmp_path)
    monkeypatch.setenv("DEVCORE_RUN_STORE", "sqlite")
    with pytest.raises(ValueError, match="forbidden"):
        DurableRunEngine(local_root=tmp_path)
    assert not list(tmp_path.rglob("*.db"))


def test_worker_refuses_unqualified_postgres_schema(monkeypatch, tmp_path):
    store = PostgresRunStore("postgresql://app:unused@127.0.0.1/fixture")
    monkeypatch.setattr(store, "verify_ready", lambda: (_ for _ in ()).throw(RuntimeError("schema absent")))
    engine = DurableRunEngine(store=store, local_root=tmp_path)
    with pytest.raises(RuntimeError, match="schema absent"):
        engine.start_worker()
    assert not engine._worker_running
    assert engine._worker_thread is None


def test_gateway_rejects_sqlite_task_path_in_team_mode(monkeypatch, tmp_path):
    from devcore_api.app import resolve_api_db_path

    database = tmp_path / "devcore.db"
    database.touch()
    monkeypatch.setenv("DEVCORE_TASK_READ_MODE", "postgres")
    monkeypatch.setenv("DEVCORE_SQLITE_DB_PATH", str(database))
    with pytest.raises(RuntimeError, match="cannot use the SQLite"):
        resolve_api_db_path()


class EffectCursor:
    def __init__(self, state):
        self.state = state
        self.result = None
        self.rowcount = 0

    def execute(self, statement, params=()):
        assert "external_effects" in statement
        if "INSERT INTO" in statement:
            if self.state["status"] in (None, "failed"):
                self.state["status"] = "pending"
                self.state["result"] = None
                self.result = ("pending",)
            else:
                self.result = None
        elif "SELECT status" in statement:
            self.result = (self.state["status"], self.state["result"])
        elif "SET status='completed'" in statement:
            self.state.update(status="completed", result=params[0])
            self.rowcount = 1
        elif "SET status='failed'" in statement:
            self.state["status"] = "failed"
            self.rowcount = 1
        else:
            raise AssertionError(statement)

    def fetchone(self):
        return self.result


def test_postgres_effect_claim_cache_and_pending(monkeypatch):
    store = PostgresRunStore("postgresql://app:unused@127.0.0.1/fixture")
    state = {"status": None, "result": None}
    projects = []

    @contextmanager
    def transaction(project_id):
        projects.append(project_id)
        yield EffectCursor(state)

    monkeypatch.setattr(store, "_transaction", transaction)
    effects = PostgresEffectIdempotencyStore(store)
    called = []
    assert effects.execute_idempotent_effect("alpha", "once", "dispatch", lambda: called.append(1) or {"ok": True}) == ({"ok": True}, True)
    assert effects.execute_idempotent_effect("alpha", "once", "dispatch", lambda: called.append(2)) == ({"ok": True}, False)
    assert called == [1]
    state["status"] = "pending"
    with pytest.raises(EffectAlreadyInProgressError):
        effects.execute_idempotent_effect("alpha", "once", "dispatch", lambda: None)
    assert projects == ["alpha"] * 4
