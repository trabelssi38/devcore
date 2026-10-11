import json

from Scripts.inspect_dropbox_conflicts import inspect


def test_conflicts_are_compared_without_writes_or_task_contents(tmp_path):
    folder = tmp_path / "Memory" / "devcore"
    folder.mkdir(parents=True)
    current = folder / "tasks.json"
    conflict = folder / "tasks (Copie en conflit de HOST 2026-08-20).json"
    current.write_text(json.dumps({"current_task": "T-1", "tasks": [
        {"id": "T-1", "title": "private current"},
        {"id": "T-2", "title": "private other"},
    ]}), encoding="utf-8")
    conflict.write_text(json.dumps({"current_task": "T-2", "tasks": [
        {"id": "T-1", "title": "private old"},
        {"id": "T-3", "title": "private lost"},
    ]}), encoding="utf-8")
    log = tmp_path / "old (conflicted copy from HOST 2026-08-20).log"
    log.write_text("log secret", encoding="utf-8")
    before = {path: path.read_bytes() for path in (current, conflict, log)}

    result = inspect(tmp_path)

    assert result["conflict_count"] == 2
    tasks = next(entry["tasks"] for entry in result["entries"] if "tasks" in entry)
    assert tasks == {
        "current_count": 2, "conflict_count": 2, "only_current": 1,
        "only_conflict": 1, "shared": 1, "changed_shared": 1,
        "changed_fields": {"title": 1}, "current_task_equal": False,
    }
    assert "private" not in json.dumps(result)
    assert all(path.read_bytes() == data for path, data in before.items())
