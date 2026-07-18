import sys
import os
import json
import time
import pytest
import yaml
from pathlib import Path
from datetime import datetime, timedelta

# Setup paths
tools_dir = Path(__file__).resolve().parent.parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

scheduler_path = tools_dir.parent / "Scheduler"
if str(scheduler_path) not in sys.path:
    sys.path.insert(0, str(scheduler_path))

import scheduler_lock
import scheduler_tick
from scheduler_contract import SchedulerJob, SchedulerJobCommand, SchedulerJobSchedule, SchedulerJobState


def test_scheduler_lease_lock(tmp_path):
    """Verify that only one owner can hold the lock lease and that it expires."""
    lock_file = tmp_path / "scheduler.lock"
    
    lock_a = scheduler_lock.SchedulerLeaseLock(lock_file, "owner_a", lease_duration_seconds=1)
    lock_b = scheduler_lock.SchedulerLeaseLock(lock_file, "owner_b", lease_duration_seconds=1)
    
    # 1. Acquire A
    assert lock_a.acquire() is True
    assert lock_a.get_owner() == "owner_a"
    
    # 2. B attempts to acquire (should fail)
    assert lock_b.acquire() is False
    assert lock_b.get_owner() == "owner_a"
    
    # 3. Wait for lease to expire
    time.sleep(1.2)
    
    # 4. B attempts to acquire (should succeed now)
    assert lock_b.acquire() is True
    assert lock_b.get_owner() == "owner_b"
    assert lock_a.acquire() is False


def test_hermes_yaml_bootstrap(tmp_path):
    """Verify that hermes_cron.yaml is successfully parsed and bootstraps jobs.json."""
    yaml_file = tmp_path / "hermes_cron.yaml"
    jobs_json = tmp_path / "jobs.json"
    
    cron_config = {
        "version": "1.0",
        "cron_tasks": [
            {
                "id": "test_cron_job",
                "name": "Test Cron Job",
                "schedule": "*/5 * * * *",
                "enabled": True,
                "catchup": True,
                "script": "dummy_script.py"
            }
        ]
    }
    
    with open(yaml_file, "w", encoding="utf-8") as f:
        yaml.dump(cron_config, f)
        
    scheduler_tick.bootstrap_jobs(yaml_file, jobs_json)
    
    assert jobs_json.exists()
    with open(jobs_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert len(data) == 1
    job = data[0]
    assert job["id"] == "test_cron_job"
    assert job["schedule"]["expr"] == "*/5 * * * *"
    assert job["policy"] == "catch_up"


def test_execute_python_command():
    """Verify executing python scripts captures stdout and stderr."""
    dummy_code = "import sys; print('STDOUT_TEST'); print('STDERR_TEST', file=sys.stderr)"
    
    command = SchedulerJobCommand(
        type="python",
        path="-c",
        args=[dummy_code]
    )
    
    ret, stdout, stderr = scheduler_tick.execute_job_command(command)
    assert ret == 0
    assert "STDOUT_TEST" in stdout
    assert "STDERR_TEST" in stderr


def test_execute_command_timeout():
    """Verify that command timeout returns -9 and timeout error messages."""
    dummy_code = "import time; time.sleep(10)"
    
    command = SchedulerJobCommand(
        type="python",
        path="-c",
        args=[dummy_code]
    )
    
    ret, stdout, stderr = scheduler_tick.execute_job_command(command, timeout=1)
    assert ret == -9
    assert "timed out after" in stderr
