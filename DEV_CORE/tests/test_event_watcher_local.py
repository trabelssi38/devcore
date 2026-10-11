"""Local event consumption must not use the shared bus or a global active project."""

import json
import os
import subprocess
import sys
from pathlib import Path

from devcore_engine.services.tasks import TaskService


PLATFORM = Path(__file__).resolve().parents[1]


def test_watcher_completes_only_named_project_and_rejects_unscoped_event(tmp_path):
    local = tmp_path / "local"
    shared = tmp_path / "shared"
    config = tmp_path / "config"
    for folder in (local, shared, config):
        folder.mkdir()
    service = TaskService(local)
    try:
        service.add_task("Alpha", project_id="alpha")
        service.add_task("Beta", project_id="beta")
        service.next_task("alpha")
        service.next_task("beta")
    finally:
        service.conn.close()

    events = local / "Bus" / "events"
    events.mkdir(parents=True)
    (events / "scoped.json").write_text(
        json.dumps({"type": "task_completed", "project": "alpha", "task_id": "T-01"}),
        encoding="utf-8",
    )
    (events / "unscoped.json").write_text(
        json.dumps({"type": "task_completed", "task_id": "T-01"}), encoding="utf-8",
    )
    old_events = shared / "Bus" / "events"
    old_events.mkdir(parents=True)
    old_event = old_events / "legacy.json"
    old_event.write_text('{"type":"task_completed","task_id":"T-01"}', encoding="utf-8")
    old_bytes = old_event.read_bytes()

    env = os.environ.copy()
    env.update({
        "DEVCORE_PLATFORM_ROOT": str(PLATFORM),
        "DEVCORE_CONFIG_ROOT": str(config),
        "DEVCORE_LOCAL_ROOT": str(local),
        "DEVCORE_DATA_ROOT": str(shared),
        "DEVCORE_PYTHON": sys.executable,
        "PYTHONPATH": str(PLATFORM),
        "DEVCORE_ACTIVE_PROJECT_NAME": "beta",
    })
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(PLATFORM / "Scripts" / "Auto" / "event_watcher.ps1")],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (local / "Bus" / "processed" / "scoped.json").exists()
    assert (local / "Bus" / "rejected" / "unscoped.json").exists()
    assert old_event.read_bytes() == old_bytes

    service = TaskService(local)
    try:
        assert service.get_task("T-01", "alpha")["status"] == "done"
        assert service.get_task("T-01", "beta")["status"] == "in_progress"
    finally:
        service.conn.close()
