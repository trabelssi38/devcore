"""Endday must not rewrite another project's note or shared memory."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from devcore_engine.db import connect_db
from devcore_engine.lifecycle.endday import EndDayManager
from devcore_engine.services.memory import MemoryService
from devcore_engine.services.tasks import TaskService


PLATFORM = Path(__file__).resolve().parents[1]


def test_endday_notes_and_events_are_project_scoped(tmp_path):
    conn = connect_db(tmp_path / "devcore.db")
    try:
        memory = MemoryService(conn)
        content = "\n".join(f"line {number}" for number in range(320))
        memory.write_text("MEMORY", content)
        tasks = TaskService(conn)
        for project in ("alpha", "beta"):
            tasks.add_task(f"Done {project}", project_id=project)
            tasks.next_task(project)
            tasks.complete_task("T-01", project_id=project)

        manager = EndDayManager(conn)
        alpha = manager.run_endday("alpha")
        beta = manager.run_endday("beta")
        assert alpha["memory_rotation"] is None
        assert beta["memory_rotation"] is None
        assert memory.get_text("MEMORY") == content

        notes = conn.execute("SELECT path, content FROM vault_notes ORDER BY path").fetchall()
        assert len(notes) == 2
        assert notes[0]["path"].startswith("Projects/alpha/Daily Notes/")
        assert notes[1]["path"].startswith("Projects/beta/Daily Notes/")
        assert "done alpha" in notes[0]["content"]
        assert "done beta" not in notes[0]["content"]
        assert "done beta" in notes[1]["content"]
        events = conn.execute(
            "SELECT project FROM bus_events WHERE event_type='EndDayCompleted' ORDER BY rowid"
        ).fetchall()
        assert [row["project"] for row in events] == ["alpha", "beta"]
        with pytest.raises(ValueError):
            manager.run_endday("../other")
    finally:
        conn.close()


def test_scheduled_endday_is_disabled_and_cli_requires_project(tmp_path):
    jobs = json.loads((PLATFORM / "Scheduler" / "jobs.devcore.json").read_text(encoding="utf-8"))
    assert next(job for job in jobs if job["id"] == "daily_endday")["enabled"] is False
    assert next(job for job in jobs if job["id"] == "weekly_maintenance")["enabled"] is False
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
        [sys.executable, "-m", "devcore_engine.cli", "endday"],
        cwd=PLATFORM, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "--project" in result.stderr
    assert not (local / "devcore.db").exists()

    weekly = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(PLATFORM / "Scripts" / "Auto" / "weekly_maintenance.ps1")],
        cwd=PLATFORM, env=env, capture_output=True, text=True, timeout=30,
        encoding="utf-8", errors="replace",
    )
    assert weekly.returncode != 0
    assert not list(shared.iterdir())


def test_explicit_weekly_maintenance_writes_only_local_outputs(tmp_path):
    platform = tmp_path / "platform"
    scripts = platform / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "platform_version.ps1").write_text("", encoding="utf-8")
    shared = tmp_path / "shared"
    memory = shared / "Memory"
    memory.mkdir(parents=True)
    (memory / "MEMORY.md").write_text("source memory", encoding="utf-8")
    shared_report = shared / "Logs" / "token_reports" / "old.txt"
    shared_report.parent.mkdir(parents=True)
    shared_report.write_text("shared unchanged", encoding="utf-8")
    local = tmp_path / "local"
    local.mkdir()
    (local / "devcore.db").write_bytes(b"fixture only")
    env = os.environ.copy()
    env.update({
        "DEVCORE_PLATFORM_ROOT": str(platform),
        "DEVCORE_LOCAL_ROOT": str(local),
        "DEVCORE_DATA_ROOT": str(shared),
    })
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(PLATFORM / "Scripts" / "Auto" / "weekly_maintenance.ps1"),
         "-RunLegacySharedMaintenance"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
        encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, result.stderr
    assert list((local / "Logs" / "scripts").glob("weekly_maintenance_*.log"))
    assert list((local / "Logs" / "token_reports").glob("*-weekly.html"))
    backups = list((local / "Backups" / "auto").glob("MEMORY_weekly_*.md"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == "source memory"
    assert shared_report.read_text(encoding="utf-8") == "shared unchanged"
    assert not (shared / "Backups").exists()
