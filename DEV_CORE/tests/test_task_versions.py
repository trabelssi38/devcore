"""Task concurrency checks against a disposable database only."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from devcore_engine.services.tasks import StaleTaskVersion, TaskService


def test_stale_edit_is_rejected_after_another_connection_changes_task(tmp_path):
    first = TaskService(tmp_path)
    second = TaskService(tmp_path)
    task = first.add_task("original", project_id="alpha")
    assert task["version"] == 1

    changed = second.edit_task(task["id"], title="new title", project_id="alpha", expected_version=1)
    assert changed["version"] == 2
    with pytest.raises(StaleTaskVersion, match="expected 1, current 2"):
        first.edit_task(task["id"], title="stale title", project_id="alpha", expected_version=1)
    assert first.get_task(task["id"], "alpha")["title"] == "new title"
    assert first.edit_task(task["id"], mode="reasoning", project_id="alpha", expected_version=2)["version"] == 3
    first.conn.close()
    second.conn.close()


def test_direct_sql_writer_advances_version(tmp_path):
    service = TaskService(tmp_path)
    task = service.add_task("original", project_id="alpha")
    service.conn.execute(
        "UPDATE tasks SET title = ? WHERE id = ? AND project_id = ?",
        ("outside writer", task["id"], "alpha"),
    )
    service.conn.commit()
    assert service.get_task(task["id"], "alpha")["version"] == 2
    with pytest.raises(StaleTaskVersion):
        service.edit_task(task["id"], title="stale", project_id="alpha", expected_version=1)
    service.conn.close()


def test_step_and_completion_reject_stale_versions_without_mutating(tmp_path):
    first = TaskService(tmp_path)
    second = TaskService(tmp_path)
    task = first.add_task("three steps", steps=3, project_id="alpha")
    changed = second.edit_task(task["id"], title="revised", project_id="alpha", expected_version=1)

    with pytest.raises(StaleTaskVersion, match="expected 1, current 2"):
        first.step_task(task["id"], project_id="alpha", expected_version=1)
    assert first.get_task(task["id"], "alpha")["steps_done"] == 0

    stepped = first.step_task(task["id"], project_id="alpha", expected_version=changed["version"])
    assert stepped["steps_done"] == 1
    assert stepped["version"] == 3

    with pytest.raises(StaleTaskVersion, match="expected 2, current 3"):
        second.complete_task(task["id"], project_id="alpha", expected_version=2)
    assert second.get_task(task["id"], "alpha")["status"] == "in_progress"
    assert second.get_task(task["id"], "alpha")["steps_done"] == 1

    completed = second.complete_task(task["id"], project_id="alpha", expected_version=3)
    assert completed["status"] == "done"
    assert completed["steps_done"] == 3
    assert completed["version"] == 4
    first.conn.close()
    second.conn.close()


def test_conditional_action_requires_explicit_task_id(tmp_path):
    service = TaskService(tmp_path)
    task = service.add_task("pending", project_id="alpha")
    with pytest.raises(ValueError, match="task_id is required"):
        service.step_task(project_id="alpha", expected_version=1)
    with pytest.raises(ValueError, match="task_id is required"):
        service.complete_task(project_id="alpha", expected_version=1)
    for action in (service.pause_task, service.skip_task, service.resume_task):
        with pytest.raises(ValueError, match="task_id is required"):
            action(project_id="alpha", expected_version=1)
    assert service.get_task(task["id"], "alpha")["status"] == "todo"
    service.conn.close()


def test_pause_skip_and_resume_reject_stale_versions(tmp_path):
    first = TaskService(tmp_path)
    second = TaskService(tmp_path)
    task = first.add_task("workflow", project_id="alpha")
    active = first.next_task("alpha")
    revised = second.edit_task(task["id"], title="revised", project_id="alpha",
                              expected_version=active["version"])

    for action in (first.pause_task, first.skip_task):
        with pytest.raises(StaleTaskVersion):
            action(task["id"], project_id="alpha", expected_version=active["version"])
    assert first.get_task(task["id"], "alpha")["status"] == "in_progress"

    paused = first.pause_task(task["id"], project_id="alpha", expected_version=revised["version"])
    assert paused["version"] == revised["version"] + 1
    with pytest.raises(StaleTaskVersion):
        second.resume_task(task["id"], project_id="alpha", expected_version=revised["version"])
    assert second.get_task(task["id"], "alpha")["status"] == "paused"

    resumed = second.resume_task(task["id"], project_id="alpha", expected_version=paused["version"])
    with pytest.raises(StaleTaskVersion):
        first.skip_task(task["id"], project_id="alpha", expected_version=paused["version"])
    skipped = first.skip_task(task["id"], project_id="alpha", expected_version=resumed["version"])
    assert skipped["status"] == "skipped"
    assert skipped["version"] == resumed["version"] + 1
    first.conn.close()
    second.conn.close()


def test_delete_rejects_stale_version_and_preserves_task(tmp_path):
    first = TaskService(tmp_path)
    second = TaskService(tmp_path)
    task = first.add_task("to retain", project_id="alpha")
    changed = second.edit_task(task["id"], title="new title", project_id="alpha",
                               expected_version=task["version"])
    with pytest.raises(StaleTaskVersion):
        first.delete_task(task["id"], "alpha", expected_version=task["version"])
    assert first.get_task(task["id"], "alpha")["title"] == "new title"
    assert first.get_task(task["id"], "alpha")["version"] == changed["version"]
    first.delete_task(task["id"], "alpha", expected_version=changed["version"])
    assert second.get_task(task["id"], "alpha") is None
    first.conn.close()
    second.conn.close()


def test_concurrent_next_selection_returns_one_active_task(tmp_path):
    seed = TaskService(tmp_path)
    seed.add_task("first", project_id="alpha")
    seed.add_task("second", project_id="alpha")
    seed.conn.close()

    def select():
        service = TaskService(tmp_path)
        try:
            return service.next_task("alpha")
        finally:
            service.conn.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        selected = list(pool.map(lambda _: select(), range(4)))
    assert {task["id"] for task in selected} == {"T-01"}
    verify = TaskService(tmp_path)
    assert [task["id"] for task in verify.get_board("alpha")["tasks"] if task["status"] == "in_progress"] == ["T-01"]
    assert verify.get_task("T-01", "alpha")["version"] == 2
    verify.conn.close()
