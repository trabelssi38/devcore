"""A normal launch must not replay stale Dropbox task JSON into SQLite."""

import json
import os
import subprocess
import sys
from pathlib import Path

from devcore_engine.db import connect_db
from devcore_engine.infra.system_watcher import SystemWatcher
from devcore_engine.lifecycle.launch import PlatformLauncher
from devcore_engine.services.tasks import TaskService


PLATFORM = Path(__file__).resolve().parents[1]


def test_launch_preserves_sql_task_state_despite_stale_shared_json(tmp_path, monkeypatch):
    local = tmp_path / "local"
    shared = tmp_path / "shared"
    local.mkdir()
    shared.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared))
    conn = connect_db(local / "devcore.db")
    try:
        tasks = TaskService(conn)
        tasks.add_task("Finished SQL", project_id="alpha")
        tasks.next_task("alpha")
        tasks.complete_task("T-01", project_id="alpha")
        tasks.add_task("Next SQL", project_id="alpha")
        stale = shared / "Memory" / "alpha" / "tasks.json"
        stale.parent.mkdir(parents=True)
        stale.write_text(json.dumps({
            "project": "alpha",
            "tasks": [{"id": "T-01", "title": "stale", "status": "todo"}],
        }), encoding="utf-8")
        before = stale.read_bytes()
        monkeypatch.setattr(SystemWatcher, "audit_and_heal", lambda self: {"services": {}})

        result = PlatformLauncher(conn).launch("alpha")
        assert result["project"] == "alpha"
        assert result["trace_id"] == result["session"]["trace_id"]
        correlations = conn.execute(
            "SELECT correlation_id FROM bus_events WHERE event_type IN "
            "('SessionStarted','PlatformLaunchCompleted') ORDER BY rowid"
        ).fetchall()
        assert [row[0] for row in correlations] == [result["trace_id"]] * 2
        assert tasks.get_task("T-01", "alpha")["status"] == "done"
        assert tasks.get_task("T-01", "alpha")["title"] == "finished sql"
        assert tasks.get_task("T-02", "alpha")["status"] == "in_progress"
        assert stale.read_bytes() == before
    finally:
        conn.close()


def test_scheduled_launch_disabled_and_cli_requires_project(tmp_path):
    jobs = json.loads((PLATFORM / "Scheduler" / "jobs.devcore.json").read_text(encoding="utf-8"))
    assert next(job for job in jobs if job["id"] == "daily_launch")["enabled"] is False
    local = tmp_path / "local"
    shared = tmp_path / "shared"
    local.mkdir()
    shared.mkdir()
    env = os.environ.copy()
    env.update({
        "DEVCORE_PLATFORM_ROOT": str(PLATFORM),
        "DEVCORE_LOCAL_ROOT": str(local),
        "DEVCORE_DATA_ROOT": str(shared),
        "PYTHONPATH": str(PLATFORM),
    })
    result = subprocess.run(
        [sys.executable, "-m", "devcore_engine.cli", "launch"],
        cwd=PLATFORM, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "--project" in result.stderr
    assert not (local / "devcore.db").exists()
