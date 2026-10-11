import pytest
from pathlib import Path
import sqlite3

from devcore_engine.db import init_db
from devcore_engine.context import RequestContext
from devcore_engine.services.tasks import TaskService
from devcore_engine.services.task_mutations import (
    TaskMutationConflict,
    complete_task_usecase,
    transition_task_usecase,
    delete_task_usecase,
)


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "devcore.db"
    conn = init_db(db_file)
    conn.execute("INSERT INTO projects(id, name, root_path) VALUES ('alpha', 'alpha', '.')")
    conn.commit()
    conn.close()
    return db_file


def test_complete_task_usecase_flow_and_conflict(test_db):
    service = TaskService(test_db.parent)
    try:
        t = service.add_task("Initial task", project_id="alpha")
        active = service.next_task("alpha")
        ver = active["version"]
    finally:
        service.conn.close()

    ctx = RequestContext(project_id="alpha", user_id="user_test")

    # Wrong expected version -> TaskMutationConflict
    with pytest.raises(TaskMutationConflict) as exc:
        complete_task_usecase("alpha", t["id"], expected_version=99, context=ctx, db_path=test_db)
    assert exc.value.code == "stale_task_version"

    # Successful completion with correct version
    success, msg = complete_task_usecase("alpha", t["id"], expected_version=ver, context=ctx, db_path=test_db)
    assert success is True
    assert "completed successfully" in msg


def test_transition_task_usecase_pause_and_resume(test_db):
    service = TaskService(test_db.parent)
    try:
        t = service.add_task("Transition task", project_id="alpha")
        active = service.next_task("alpha")
        ver = active["version"]
    finally:
        service.conn.close()

    ctx = RequestContext(project_id="alpha", user_id="user_test")

    # Pause
    ok = transition_task_usecase("alpha", t["id"], "pause", expected_version=ver, context=ctx, db_path=test_db)
    assert ok is True

    # Check paused
    service = TaskService(test_db.parent)
    try:
        paused = service.get_task(t["id"], "alpha")
        assert paused["status"] == "paused"
        paused_ver = paused["version"]
    finally:
        service.conn.close()

    # Resume with wrong version -> Conflict
    with pytest.raises(TaskMutationConflict):
        transition_task_usecase("alpha", t["id"], "resume", expected_version=99, context=ctx, db_path=test_db)

    # Resume with correct version
    ok_resume = transition_task_usecase("alpha", t["id"], "resume", expected_version=paused_ver, context=ctx, db_path=test_db)
    assert ok_resume is True


def test_delete_task_usecase_with_dependencies(test_db):
    service = TaskService(test_db.parent)
    try:
        parent = service.add_task("Parent task", project_id="alpha")
        child = service.add_task("Child task", project_id="alpha", depends_on=parent["id"])
    finally:
        service.conn.close()

    ctx = RequestContext(project_id="alpha", user_id="user_test")

    # Cannot delete parent while child depends on it
    ok, reason = delete_task_usecase("alpha", parent["id"], context=ctx, db_path=test_db)
    assert ok is False
    assert "is required by" in reason

    # Delete child first
    ok_child, _ = delete_task_usecase("alpha", child["id"], context=ctx, db_path=test_db)
    assert ok_child is True

    # Now parent can be deleted
    ok_parent, _ = delete_task_usecase("alpha", parent["id"], context=ctx, db_path=test_db)
    assert ok_parent is True
