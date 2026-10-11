"""History publication failures must never advance the scheduler state."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scheduler"))
import scheduler_history
import scheduler_tick


def test_update_missing_history_row_is_failure(tmp_path):
    path = tmp_path / "history.db"
    scheduler_history.init_db(path)
    assert scheduler_history.update_run("job", "date", 1, "ok", db_path=path) is False


def test_failed_update_preserves_running_claim(tmp_path):
    path = tmp_path / "history.db"
    assert scheduler_history.record_run("job", "date", "started", 0, "running", db_path=path)
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TRIGGER fixture_denial BEFORE UPDATE ON run_history BEGIN SELECT RAISE(ABORT, 'fixture storage failure'); END")
    assert scheduler_history.update_run("job", "date", 1, "ok", db_path=path) is False
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT status,duration FROM run_history").fetchone() == ("running", 0)


def test_cycle_does_not_advance_when_history_result_cannot_be_saved(tmp_path, monkeypatch, caplog):
    class EndFixtureLoop(BaseException):
        pass
    scheduled = datetime.now(timezone.utc).isoformat()
    job = SimpleNamespace(id="fixture", enabled=True, timezone="UTC", command=None,
        state=SimpleNamespace(next_run_at=scheduled, completed_count=0))
    monkeypatch.setattr(scheduler_tick, "load_jobs", lambda path: [job])
    monkeypatch.setattr(scheduler_tick, "_ensure_aware", lambda *a: datetime.now(timezone.utc))
    monkeypatch.setattr(scheduler_tick, "compute_next_run", lambda *a: pytest.fail("No advancement after failed history"))
    monkeypatch.setattr(scheduler_tick.scheduler_history, "init_db", lambda *a: None)
    monkeypatch.setattr(scheduler_tick.scheduler_history, "is_run_completed", lambda *a: False)
    monkeypatch.setattr(scheduler_tick.scheduler_history, "record_run", lambda **k: True)
    monkeypatch.setattr(scheduler_tick.scheduler_history, "update_run", lambda **k: False)
    monkeypatch.setattr(scheduler_tick, "execute_job_command", lambda *a: (0, "fixture", ""))
    monkeypatch.setattr(scheduler_tick, "save_jobs", lambda *a: pytest.fail("No schedule save after failed history"))
    def stop(seconds):
        raise EndFixtureLoop()
    monkeypatch.setattr(scheduler_tick.time, "sleep", stop)
    with pytest.raises(EndFixtureLoop):
        scheduler_tick.main_loop(tmp_path / "history.db", tmp_path / "jobs.json", tmp_path / "scheduler.lock")
    assert job.state.next_run_at == scheduled and job.state.completed_count == 0
    assert "result could not be persisted" in caplog.text


@pytest.mark.parametrize("status,completed", [("running", False), ("error", False), ("ok", True), ("skipped", True)])
def test_only_terminal_success_or_skip_allows_schedule_advancement(tmp_path, status, completed):
    path = tmp_path / "history.db"
    assert scheduler_history.record_run("job", "date", "started", 0, status, db_path=path)
    assert scheduler_history.is_run_completed("job", "date", path) is completed


@pytest.mark.parametrize("status", ["running", "error"])
def test_existing_unresolved_claim_neither_reexecutes_nor_advances(tmp_path, monkeypatch, caplog, status):
    class EndFixtureLoop(BaseException):
        pass
    path = tmp_path / "history.db"
    scheduled = datetime.now(timezone.utc).isoformat()
    assert scheduler_history.record_run("fixture", scheduled, "started", 0, status, db_path=path)
    job = SimpleNamespace(id="fixture", enabled=True, timezone="UTC", command=None,
        state=SimpleNamespace(next_run_at=scheduled, completed_count=0))
    monkeypatch.setattr(scheduler_tick, "load_jobs", lambda path: [job])
    monkeypatch.setattr(scheduler_tick, "_ensure_aware", lambda *a: datetime.now(timezone.utc))
    monkeypatch.setattr(scheduler_tick, "compute_next_run", lambda *a: pytest.fail("Unresolved claim must not advance"))
    monkeypatch.setattr(scheduler_tick, "execute_job_command", lambda *a: pytest.fail("Unresolved effects must not repeat"))
    monkeypatch.setattr(scheduler_tick, "save_jobs", lambda *a: pytest.fail("Unchanged registry must not be rewritten"))
    def stop(seconds):
        raise EndFixtureLoop()
    monkeypatch.setattr(scheduler_tick.time, "sleep", stop)
    with pytest.raises(EndFixtureLoop):
        scheduler_tick.main_loop(path, tmp_path / "jobs.json", tmp_path / "scheduler.lock")
    assert job.state.next_run_at == scheduled and job.state.completed_count == 0
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT status,count(*) FROM run_history").fetchone() == (status, 1)
    assert "pending reconciliation" in caplog.text
