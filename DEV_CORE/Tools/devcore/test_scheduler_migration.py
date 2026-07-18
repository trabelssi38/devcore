import sys
import os
import json
from pathlib import Path
from datetime import datetime
import pytest

# Ensure devcore is in path
tools_dir = Path(__file__).resolve().parent.parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

# Add Scheduler to path
scheduler_dir = tools_dir.parent / "Scheduler"
if str(scheduler_dir) not in sys.path:
    sys.path.insert(0, str(scheduler_dir))

import scheduler_sync
from scheduler_contract import SchedulerJob, SchedulerJobSchedule, SchedulerJobCommand, SchedulerJobState


def test_sync_registry_new_and_merge(tmp_path):
    """Test registry synchronization and state merging."""
    static_dir = tmp_path / "Scheduler"
    static_dir.mkdir()
    static_file = static_dir / "jobs.devcore.json"
    
    # Static config definition
    static_jobs = [
        {
            "schema_version": 1,
            "id": "job_a",
            "name": "Job A",
            "enabled": True,
            "no_agent": True,
            "schedule": {"kind": "cron", "expr": "*/5 * * * *"},
            "command": {"type": "python", "path": "test_a.py", "args": []},
            "state": {"next_run_at": None, "last_run_at": None, "last_status": None, "completed": 0},
            "policy": "skip",
            "timezone": "Europe/Paris"
        },
        {
            "schema_version": 1,
            "id": "job_b",
            "name": "Job B",
            "enabled": True,
            "no_agent": True,
            "schedule": {"kind": "cron", "expr": "0 * * * *"},
            "command": {"type": "python", "path": "test_b.py", "args": []},
            "state": {"next_run_at": None, "last_run_at": None, "last_status": None, "completed": 0},
            "policy": "skip",
            "timezone": "Europe/Paris"
        }
    ]
    with open(static_file, "w", encoding="utf-8") as f:
        json.dump(static_jobs, f)

    dynamic_dir = tmp_path / "Dynamic"
    dynamic_dir.mkdir()
    dynamic_file = dynamic_dir / "Scheduler" / "jobs.json"
    
    # Pre-existing dynamic state for Job A (completed = 5, last_run_at = earlier)
    pre_existing = [
        {
            "schema_version": 1,
            "id": "job_a",
            "name": "Job A Old Name",
            "enabled": False, # Will be overwritten by static enabled: True
            "no_agent": True,
            "schedule": {"kind": "cron", "expr": "*/10 * * * *"}, # Will be overwritten
            "command": {"type": "python", "path": "test_a.py", "args": []},
            "state": {
                "next_run_at": "2026-07-18T12:00:00+02:00",
                "last_run_at": "2026-07-18T11:50:00+02:00",
                "last_status": "ok",
                "last_error": None,
                "completed": 5
            },
            "policy": "skip",
            "timezone": "Europe/Paris"
        }
    ]
    dynamic_file.parent.mkdir(parents=True, exist_ok=True)
    with open(dynamic_file, "w", encoding="utf-8") as f:
        json.dump(pre_existing, f)

    # Sync
    scheduler_sync.sync_registry(tmp_path, dynamic_dir)

    # Validate output file
    assert dynamic_file.exists()
    with open(dynamic_file, "r", encoding="utf-8") as f:
        merged = json.load(f)

    assert len(merged) == 2
    
    # Job A check (should have merged state)
    job_a = next(j for j in merged if j["id"] == "job_a")
    assert job_a["name"] == "Job A"  # Updated name
    assert job_a["enabled"] is True # Updated enabled
    assert job_a["schedule"]["expr"] == "*/5 * * * *" # Updated schedule
    assert job_a["state"]["completed"] == 5 # Preserved state count
    assert job_a["state"]["last_run_at"] == "2026-07-18T11:50:00+02:00" # Preserved status
    assert job_a["state"]["next_run_at"] == "2026-07-18T12:00:00+02:00" # Preserved next_run_at

    # Job B check (new job, should have next_run_at computed)
    job_b = next(j for j in merged if j["id"] == "job_b")
    assert job_b["name"] == "Job B"
    assert job_b["state"]["completed"] == 0
    assert job_b["state"]["next_run_at"] is not None


def test_cli_scheduler_status(capsys, monkeypatch, tmp_path):
    """Test cmd_scheduler_status CLI command formatting."""
    jobs_file = tmp_path / "Scheduler" / "jobs.json"
    jobs_data = [
        {
            "schema_version": 1,
            "id": "periodic_task_scan",
            "name": "DEV_CORE Periodic Task Scan",
            "enabled": True,
            "no_agent": True,
            "schedule": {"kind": "cron", "expr": "*/10 * * * *"},
            "command": {"type": "powershell", "path": "DEV_CORE/Scripts/task_scan.ps1", "args": []},
            "state": {
                "next_run_at": "2026-07-18T15:50:00+02:00",
                "last_run_at": "2026-07-18T15:40:00+02:00",
                "last_status": "ok",
                "last_error": None,
                "completed": 12
            },
            "policy": "skip",
            "timezone": "Europe/Paris"
        }
    ]
    jobs_file.parent.mkdir(parents=True, exist_ok=True)
    with open(jobs_file, "w", encoding="utf-8") as f:
        json.dump(jobs_data, f)

    # Monkeypatch get_data_root to point to tmp_path
    import dc
    monkeypatch.setattr(dc, "get_data_root", lambda: tmp_path)

    # Run command
    dc.cmd_scheduler_status(None)
    
    captured = capsys.readouterr()
    assert "DEV_CORE Scheduler Status" in captured.out
    assert "periodic_task_scan" in captured.out
    assert "Yes" in captured.out
    assert "cron" in captured.out
    assert "*/10 * * * *" in captured.out
    assert "ok" in captured.out
    assert "12" in captured.out
