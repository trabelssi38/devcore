"""Regression tests for project-scoped task IDs and session state."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from devcore_engine.db import connect_db
from devcore_engine.lifecycle.session import SessionManager
from devcore_engine.services.tasks import TaskService


def test_duplicate_task_ids_are_isolated(tmp_path):
    service = TaskService(tmp_path)
    a = service.add_task("A", project_id="alpha", steps=2)
    b = service.add_task("B", project_id="beta", steps=2)
    assert a["id"] == b["id"] == "T-01"

    assert service.get_task("T-01", "alpha")["title"] == "a"
    assert service.get_task("T-01", "beta")["title"] == "b"
    assert service.get_task("T-01", "gamma") is None

    service.edit_task("T-01", title="A edited", project_id="alpha")
    service.next_task("alpha")
    service.step_task("T-01", project_id="alpha")
    assert service.get_task("T-01", "alpha")["steps_done"] == 1
    assert service.get_task("T-01", "beta")["steps_done"] == 0
    assert service.get_task("T-01", "beta")["status"] == "todo"
    assert service.get_task("T-01", "beta")["title"] == "b"

    assert service.complete_task("T-01", project_id="gamma") is None
    service.complete_task("T-01", project_id="alpha")
    assert service.get_task("T-01", "alpha")["status"] == "done"
    assert service.get_task("T-01", "beta")["status"] == "todo"


def test_dependency_must_belong_to_same_project(tmp_path):
    service = TaskService(tmp_path)
    service.add_task("A", project_id="alpha")
    service.complete_task("T-01", project_id="alpha")
    service.add_task("B", project_id="beta", depends_on="T-01")
    assert service.next_task("beta") is None


def test_fresh_schema_rejects_cross_project_task_reference(tmp_path):
    conn = connect_db(tmp_path / "devcore.db")
    service = TaskService(conn)
    service.add_task("A", project_id="alpha")
    service.add_task("A2", project_id="alpha")
    service.add_task("B", project_id="beta")
    conn.execute("INSERT INTO runs(id, project_id, task_id) VALUES ('good', 'alpha', 'T-01')")
    conn.commit()
    try:
        conn.execute("INSERT INTO runs(id, project_id, task_id) VALUES ('bad', 'beta', 'T-02')")
    except sqlite3.IntegrityError:
        conn.rollback()
    else:
        raise AssertionError("cross-project task reference was accepted")
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_session_state_is_per_manager(tmp_path):
    conn = connect_db(tmp_path / "devcore.db")
    first = SessionManager(conn)
    second = SessionManager(conn)
    first.set_active_project("alpha")
    second.set_active_project("beta")
    assert first.get_active_project() == "alpha"
    assert second.get_active_project() == "beta"
    assert conn.execute("SELECT value FROM runtime_state WHERE key='active_project'").fetchone() is None


def test_concurrent_number_allocation(tmp_path):
    db_path = tmp_path / "devcore.db"
    connect_db(db_path).close()

    def create(index):
        service = TaskService(tmp_path)
        try:
            return service.add_task(f"Task {index}", project_id="alpha")["id"]
        finally:
            service.conn.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(create, range(12)))
    assert len(ids) == len(set(ids)) == 12


def test_mutations_require_an_explicit_project(tmp_path):
    service = TaskService(tmp_path)
    with pytest.raises(ValueError):
        service.add_task("no project")
    with pytest.raises(ValueError):
        service.step_task("T-01")
    with pytest.raises(ValueError):
        service.complete_task("T-01")
    with pytest.raises(ValueError):
        service.edit_task("T-01", title="wrong")


def test_task_import_key_is_idempotent(tmp_path):
    service = TaskService(tmp_path)
    first = service.add_task("Imported", project_id="alpha", idempotency_key="queue-1")
    repeated = service.add_task("Changed", project_id="alpha", idempotency_key="queue-1")
    assert repeated["id"] == first["id"]
    assert repeated["title"] == "imported"
    assert len(service.get_board("alpha")["tasks"]) == 1


def test_project_id_cannot_escape_legacy_export_root(tmp_path):
    service = TaskService(tmp_path)
    with pytest.raises(ValueError):
        service.add_task("bad", project_id="../outside")
    with pytest.raises(ValueError):
        service.get_board("../outside")
    with pytest.raises(ValueError):
        service.export_legacy_json("../outside", tmp_path)


def test_task_mutations_do_not_write_legacy_json_without_explicit_export(tmp_path):
    shared = tmp_path / "shared"
    legacy_file = shared / "Memory" / "alpha" / "tasks.json"
    legacy_file.parent.mkdir(parents=True)
    legacy_file.write_text("legacy snapshot", encoding="utf-8")
    service = TaskService(tmp_path / "local")
    try:
        created = service.add_task("Current", project_id="alpha")
        service.next_task("alpha")
        service.complete_task(created["id"], project_id="alpha")
        assert legacy_file.read_text(encoding="utf-8") == "legacy snapshot"

        exported = service.export_legacy_json("alpha", shared)
        assert exported == legacy_file
        import json
        assert json.loads(exported.read_text(encoding="utf-8"))["tasks"][0]["status"] == "done"
    finally:
        service.conn.close()


def test_concurrent_import_with_same_key_creates_one_task(tmp_path):
    TaskService(tmp_path).conn.close()

    def import_once(index):
        service = TaskService(tmp_path)
        try:
            return service.add_task(
                f"Import {index}", project_id="alpha", idempotency_key="same-queue-line"
            )["id"]
        finally:
            service.conn.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(import_once, range(4)))
    assert ids == ["T-01"] * 4
    service = TaskService(tmp_path)
    assert len(service.get_board("alpha")["tasks"]) == 1
    service.conn.close()


def test_delete_retains_history_and_blocks_active_dependents(tmp_path):
    service = TaskService(tmp_path)
    first = service.add_task("First", project_id="alpha", idempotency_key="queue-1")
    service.add_task("Dependent", project_id="alpha", depends_on=first["id"])
    service.add_task("Other", project_id="beta")
    service.conn.execute(
        "INSERT INTO runs(id, project_id, task_id) VALUES ('run-1', 'alpha', ?)",
        (first["id"],),
    )
    service.conn.commit()

    with pytest.raises(ValueError, match="is required by"):
        service.delete_task(first["id"], "alpha")
    assert service.get_task(first["id"], "alpha") is not None

    service.complete_task("T-02", project_id="alpha")
    deleted = service.delete_task(first["id"], "alpha")
    assert deleted["id"] == first["id"]
    assert service.get_task(first["id"], "alpha") is None
    assert service.complete_task(first["id"], project_id="alpha") is None
    assert service.get_task("T-01", "beta")["status"] == "todo"
    assert [task["id"] for task in service.get_board("alpha")["tasks"]] == ["T-02"]
    assert service.conn.execute(
        "SELECT status FROM tasks WHERE id = ? AND project_id = 'alpha'", (first["id"],)
    ).fetchone()[0] == "deleted"
    assert service.conn.execute("SELECT task_id FROM runs WHERE id = 'run-1'").fetchone()[0] == first["id"]
    assert service.conn.execute("PRAGMA foreign_key_check").fetchall() == []
    with pytest.raises(ValueError, match="deleted task"):
        service.add_task("Replay", project_id="alpha", idempotency_key="queue-1")
