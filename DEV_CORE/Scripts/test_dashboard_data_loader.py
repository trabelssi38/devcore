import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard.data_loader import load_projects_and_tasks, load_token_metrics


def _write_stale_json(data_root: Path) -> None:
    project_dir = data_root / "Memory" / "alpha"
    project_dir.mkdir(parents=True)
    (project_dir / "tasks.json").write_text(
        json.dumps({"current_task": "T-1", "tasks": [{"id": "T-1", "title": "Old", "status": "active"}]}),
        encoding="utf-8",
    )


def test_token_metrics_do_not_fall_back_to_stale_shared_report(tmp_path):
    local = tmp_path / "local"
    shared = tmp_path / "shared"
    old_report = shared / "Logs" / "token_reports" / "token_metrics_summary.json"
    old_report.parent.mkdir(parents=True)
    old_report.write_text(json.dumps({"source": "shared"}), encoding="utf-8")
    assert load_token_metrics(local) == {}
    local_report = local / "Logs" / "token_reports" / "token_metrics_summary.json"
    local_report.parent.mkdir(parents=True)
    local_report.write_text(json.dumps({"source": "local"}), encoding="utf-8")
    assert load_token_metrics(local) == {"source": "local"}
    assert old_report.read_text(encoding="utf-8") == json.dumps({"source": "shared"})


def test_dashboard_does_not_restore_stale_json_tasks(tmp_path):
    data_root = tmp_path / "shared"
    local_root = tmp_path / "local"
    local_root.mkdir()
    _write_stale_json(data_root)
    db_path = local_root / "devcore.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE tasks (id TEXT, project_id TEXT, title TEXT, status TEXT, mode TEXT, "
            "steps_total INTEGER, steps_done INTEGER, metadata TEXT, started_at TEXT, "
            "completed_at TEXT, created_at TEXT, updated_at TEXT)"
        )
        conn.execute(
            "INSERT INTO tasks VALUES ('T-1', 'alpha', 'Current', 'done', 'coding', 1, 1, '', '', '', '', '')"
        )

    projects, _ = load_projects_and_tasks(data_root, tmp_path, local_root=local_root)
    assert projects[0]["tasks"][0]["status"] == "done"
    assert projects[0]["tasks"][0]["title"] == "Current"
    assert projects[0]["tasks"][0]["version"] is None
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT title, status FROM tasks").fetchone() == ("Current", "done")
        conn.execute("UPDATE tasks SET status = 'deleted'")

    projects, _ = load_projects_and_tasks(data_root, tmp_path, local_root=local_root)
    assert projects == []
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT status FROM tasks").fetchone()[0] == "deleted"


def test_dashboard_read_error_does_not_fall_back_to_stale_json(tmp_path):
    data_root = tmp_path / "shared"
    local_root = tmp_path / "local"
    local_root.mkdir()
    _write_stale_json(data_root)
    (local_root / "devcore.db").write_text("invalid SQLite", encoding="utf-8")

    with pytest.raises(sqlite3.DatabaseError):
        load_projects_and_tasks(data_root, tmp_path, local_root=local_root)


def test_dashboard_requires_explicit_legacy_mode_without_database(tmp_path, monkeypatch):
    data_root = tmp_path / "shared"
    local_root = tmp_path / "local"
    _write_stale_json(data_root)
    monkeypatch.delenv("DEVCORE_DASHBOARD_LEGACY_JSON", raising=False)

    projects, _ = load_projects_and_tasks(data_root, tmp_path, local_root=local_root)
    assert projects == []
    assert not (local_root / "devcore.db").exists()

    monkeypatch.setenv("DEVCORE_DASHBOARD_LEGACY_JSON", "1")
    projects, _ = load_projects_and_tasks(data_root, tmp_path, local_root=local_root)
    assert projects[0]["tasks"][0]["id"] == "T-1"


def test_dashboard_snapshot_keeps_observed_task_version(tmp_path):
    data_root = tmp_path / "shared"
    local_root = tmp_path / "local"
    local_root.mkdir()
    _write_stale_json(data_root)
    database = local_root / "devcore.db"
    with sqlite3.connect(database) as conn:
        conn.execute("""CREATE TABLE tasks(id TEXT, project_id TEXT, title TEXT,
            status TEXT, mode TEXT, steps_total INTEGER, steps_done INTEGER,
            metadata TEXT, started_at TEXT, completed_at TEXT, created_at TEXT,
            updated_at TEXT, version INTEGER)""")
        conn.execute("INSERT INTO tasks VALUES ('T-1','alpha','SQL','todo','coding',1,0,'','','','','',7)")
    first, _ = load_projects_and_tasks(data_root, tmp_path, local_root=local_root)
    with sqlite3.connect(database) as writer:
        writer.execute("UPDATE tasks SET title='Other writer', version=8")
    second, _ = load_projects_and_tasks(data_root, tmp_path, local_root=local_root)
    assert first[0]["tasks"][0]["version"] == 7
    assert second[0]["tasks"][0]["version"] == 8
    assert first[0]["tasks"][0]["title"] == "SQL"
    assert second[0]["tasks"][0]["title"] == "Other writer"
