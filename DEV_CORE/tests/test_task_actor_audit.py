"""Transactional author history on disposable business databases."""

from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3

import pytest

from devcore_engine.context import RequestContext
from devcore_engine.services.tasks import StaleTaskVersion, TaskService


@pytest.mark.parametrize("operation,action,status", [
    ("complete_task", "task.complete", "done"), ("delete_task", "task.delete", "deleted"),
])
def test_actor_history_preserves_project_identity_and_committed_versions(tmp_path, operation, action, status):
    service = TaskService(tmp_path)
    try:
        task = service.add_task("private title not for audit", project_id="alpha")
        service.add_task("same identifier other project", project_id="beta")
        context = RequestContext("alpha", user_id="alice", session_id="session-id", trace_id="trace-id")
        getattr(service, operation)(task["id"], "alpha", expected_version=1, context=context)
        row = dict(service.conn.execute("SELECT * FROM audit_log").fetchone())
        assert (row["actor"], row["project_id"], row["task_id"], row["action"], row["entity_id"]) == (
            "alice", "alpha", task["id"], action, task["id"],
        )
        assert json.loads(row["details"]) == {
            "schema_version": 1, "trace_id": "trace-id", "session_id": "session-id",
            "before": {"status": "todo", "version": 1}, "after": {"status": status, "version": 2},
        }
        assert "private title" not in row["details"]
        assert service.get_task(task["id"], "beta")["status"] == "todo"
        assert service.conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        service.conn.close()


@pytest.mark.parametrize("operation", ["complete_task", "delete_task"])
def test_audit_failure_rolls_back_task_version_and_events(tmp_path, operation):
    service = TaskService(tmp_path)
    try:
        task = service.add_task("fixture", project_id="alpha")
        events_before = service.conn.execute("SELECT COUNT(*) FROM bus_events").fetchone()[0]
        service.conn.execute("CREATE TRIGGER reject_audit BEFORE INSERT ON audit_log "
                             "BEGIN SELECT RAISE(ABORT, 'audit fixture unavailable'); END")
        service.conn.commit()
        with pytest.raises(sqlite3.IntegrityError, match="audit fixture unavailable"):
            getattr(service, operation)(task["id"], "alpha", expected_version=1,
                                        context=RequestContext("alpha", user_id="alice"))
        retained = service.get_task(task["id"], "alpha")
        assert (retained["status"], retained["version"]) == ("todo", 1)
        assert service.conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0
        assert service.conn.execute("SELECT COUNT(*) FROM bus_events").fetchone()[0] == events_before
    finally:
        service.conn.close()


def test_rejected_edits_and_missing_tasks_do_not_create_success_history(tmp_path):
    service = TaskService(tmp_path)
    try:
        task = service.add_task("fixture", project_id="alpha")
        for operation in (service.complete_task, service.delete_task):
            for invalid in (RequestContext("beta", user_id="alice"), RequestContext("alpha")):
                with pytest.raises(ValueError, match="audit context"):
                    operation(task["id"], "alpha", expected_version=1, context=invalid)
            with pytest.raises(StaleTaskVersion):
                operation(task["id"], "alpha", expected_version=2,
                          context=RequestContext("alpha", user_id="alice"))
            assert operation("T-missing", "alpha", expected_version=1,
                             context=RequestContext("alpha", user_id="alice")) is None
        assert service.conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0
        assert service.get_task(task["id"], "alpha")["version"] == 1
    finally:
        service.conn.close()


def test_concurrent_same_version_records_only_the_winning_actor(tmp_path):
    seed = TaskService(tmp_path)
    task = seed.add_task("fixture", project_id="alpha")
    seed.conn.close()

    def mutate(user):
        service = TaskService(tmp_path)
        try:
            service.complete_task(task["id"], "alpha", expected_version=1,
                                  context=RequestContext("alpha", user_id=user))
            return user
        except StaleTaskVersion:
            return None
        finally:
            service.conn.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(mutate, ("alice", "bob")))
    winners = [user for user in results if user is not None]
    assert len(winners) == 1
    with sqlite3.connect(tmp_path / "devcore.db") as conn:
        assert conn.execute("SELECT actor FROM audit_log").fetchall() == [(winners[0],)]
        assert conn.execute("SELECT status,version FROM tasks WHERE project_id='alpha'").fetchone() == ("done", 2)


@pytest.mark.parametrize("operation,action,source,target", [
    ("pause_task", "task.pause", "in_progress", "paused"),
    ("resume_task", "task.resume", "paused", "in_progress"),
])
def test_pause_resume_history_and_rejections(tmp_path, operation, action, source, target):
    from devcore_engine.security.identity import AUDIT_READ, Principal
    from devcore_engine.services.task_audit import read_task_audit
    service = TaskService(tmp_path)
    try:
        task = service.add_task("private fixture", project_id="alpha")
        service.add_task("beta", project_id="beta")
        service.next_task("alpha")
        if operation == "resume_task":
            service.pause_task(task["id"], "alpha")
        original = service.get_task(task["id"], "alpha")
        mutate = getattr(service, operation)
        for context in (RequestContext("beta", user_id="alice"), RequestContext("alpha")):
            with pytest.raises(ValueError, match="audit context"):
                mutate(task["id"], "alpha", expected_version=original["version"], context=context)
        with pytest.raises(StaleTaskVersion):
            mutate(task["id"], "alpha", expected_version=original["version"] + 1,
                   context=RequestContext("alpha", user_id="alice"))
        assert mutate("T-missing", "alpha", expected_version=1,
                      context=RequestContext("alpha", user_id="alice")) is None
        assert service.conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0
        changed = mutate(task["id"], "alpha", expected_version=original["version"],
                         context=RequestContext("alpha", user_id="alice", trace_id="fixture-trace"))
        assert (changed["status"], changed["version"]) == (target, original["version"] + 1)
        # A repeated request never adds successful history (resume rejects an active task).
        with pytest.raises((StaleTaskVersion, ValueError)):
            mutate(task["id"], "alpha", expected_version=original["version"],
                   context=RequestContext("alpha", user_id="bob"))
        page = read_task_audit(tmp_path / "devcore.db", Principal("alice", "fixture-credential", "alpha", AUDIT_READ))
        assert len(page["events"]) == 1
        event = page["events"][0]
        assert event["action"] == action and event["actor"] == "alice"
        assert event["before"] == {"status": source, "version": original["version"]}
        assert event["after"] == {"status": target, "version": original["version"] + 1}
        assert "fixture-trace" not in json.dumps(page) and "private fixture" not in json.dumps(page)
        assert service.get_task(task["id"], "beta")["version"] == 1
    finally:
        service.conn.close()


@pytest.mark.parametrize("operation", ["pause_task", "resume_task"])
def test_pause_resume_audit_failure_restores_entire_transaction(tmp_path, operation):
    service = TaskService(tmp_path)
    try:
        task = service.add_task("fixture", project_id="alpha")
        service.next_task("alpha")
        if operation == "resume_task":
            service.pause_task(task["id"], "alpha")
        original = service.get_task(task["id"], "alpha")
        events = service.conn.execute("SELECT COUNT(*) FROM bus_events").fetchone()[0]
        service.conn.execute("CREATE TRIGGER reject_audit BEFORE INSERT ON audit_log "
                             "BEGIN SELECT RAISE(ABORT, 'fixture audit failure'); END")
        service.conn.commit()
        with pytest.raises(sqlite3.IntegrityError, match="fixture audit failure"):
            getattr(service, operation)(task["id"], "alpha", expected_version=original["version"],
                                        context=RequestContext("alpha", user_id="alice"))
        assert not service.conn.in_transaction
        assert service.get_task(task["id"], "alpha") == original
        assert service.conn.execute("SELECT COUNT(*) FROM bus_events").fetchone()[0] == events
        assert service.conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0
    finally:
        service.conn.close()


@pytest.mark.parametrize("action,source,target", [
    ("task.pause", "todo", "paused"), ("task.resume", "done", "in_progress"),
])
def test_audit_reader_refuses_forged_pause_resume_transitions(action, source, target):
    from uuid import uuid4
    from devcore_engine.services.task_audit import project_row
    row = {"id": str(uuid4()), "project_id": "alpha", "entity_type": "task", "entity_id": "T-01",
           "task_id": "T-01", "actor": "alice", "action": action, "created_at": "2026-10-05 12:00:00",
           "details": json.dumps({"schema_version": 1, "before": {"status": source, "version": 1},
                                  "after": {"status": target, "version": 2}})}
    with pytest.raises(ValueError, match="Invalid audited transition"):
        project_row(row, "alpha")
