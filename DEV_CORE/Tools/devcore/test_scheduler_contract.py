import sys
import os
import sqlite3
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Setup sys.path to import modules correctly
tools_dir = Path(__file__).resolve().parent.parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

scripts_dir = tools_dir.parent / "Scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

scheduler_path = tools_dir.parent / "Scheduler"
if str(scheduler_path) not in sys.path:
    sys.path.insert(0, str(scheduler_path))

from scheduler_contract import (
    SchedulerJob,
    SchedulerJobSchedule,
    SchedulerJobCommand,
    SchedulerJobState,
    compute_next_run,
    _ensure_aware
)
import scheduler_history


def test_job_validation():
    """Verify that SchedulerJob validates correct job configurations and handles defaults."""
    job_data = {
        "id": "test_job",
        "name": "Test Job",
        "schedule": {"kind": "cron", "expr": "0 10 * * *"},
        "command": {"type": "python", "path": "test.py", "args": ["--verbose"]},
        "timezone": "Europe/Paris"
    }
    job = SchedulerJob(**job_data)
    assert job.id == "test_job"
    assert job.enabled is True
    assert job.no_agent is True
    assert job.state.completed_count == 0


def test_next_run_once_future():
    """Verify compute_next_run for 'once' schedule in the future."""
    future_time = datetime.now(ZoneInfo("Europe/Paris")) + timedelta(hours=2)
    job = SchedulerJob(
        id="once_job",
        name="Once Job",
        schedule=SchedulerJobSchedule(kind="once", expr=future_time.isoformat()),
        command=SchedulerJobCommand(type="python", path="test.py")
    )
    next_run = compute_next_run(job, datetime.now(ZoneInfo("Europe/Paris")))
    assert next_run is not None
    assert next_run == future_time


def test_next_run_once_past_with_grace():
    """Verify compute_next_run for 'once' schedule in the past but within grace period."""
    past_time = datetime.now(ZoneInfo("Europe/Paris")) - timedelta(minutes=30)
    job = SchedulerJob(
        id="once_job",
        name="Once Job",
        schedule=SchedulerJobSchedule(kind="once", expr=past_time.isoformat()),
        command=SchedulerJobCommand(type="python", path="test.py")
    )
    next_run = compute_next_run(job, datetime.now(ZoneInfo("Europe/Paris")))
    assert next_run is not None
    assert next_run == past_time


def test_next_run_once_past_no_grace():
    """Verify compute_next_run for 'once' schedule in the past beyond grace period returns None."""
    past_time = datetime.now(ZoneInfo("Europe/Paris")) - timedelta(hours=3)
    job = SchedulerJob(
        id="once_job",
        name="Once Job",
        schedule=SchedulerJobSchedule(kind="once", expr=past_time.isoformat()),
        command=SchedulerJobCommand(type="python", path="test.py")
    )
    next_run = compute_next_run(job, datetime.now(ZoneInfo("Europe/Paris")))
    assert next_run is None


def test_next_run_interval_skip(tmp_path):
    """Verify compute_next_run with policy 'skip' for interval jobs."""
    now = datetime(2026, 7, 18, 12, 0, 0, tzinfo=ZoneInfo("Europe/Paris"))
    last_run = now - timedelta(hours=4) # 8:00
    
    # Scheduled for every 60 minutes
    # If policy is 'skip', next run must be strictly in the future of now (e.g. 13:00)
    job = SchedulerJob(
        id="interval_job",
        name="Interval Job",
        schedule=SchedulerJobSchedule(kind="interval", expr="60"),
        command=SchedulerJobCommand(type="python", path="test.py"),
        policy="skip",
        state=SchedulerJobState(last_run_at=last_run.isoformat())
    )
    next_run = compute_next_run(job, now)
    assert next_run == datetime(2026, 7, 18, 13, 0, 0, tzinfo=ZoneInfo("Europe/Paris"))


def test_next_run_interval_run_once():
    """Verify compute_next_run with policy 'run_once' for interval jobs."""
    now = datetime(2026, 7, 18, 12, 0, 0, tzinfo=ZoneInfo("Europe/Paris"))
    last_run = now - timedelta(hours=3) # 9:00
    
    # Missed runs at 10:00, 11:00, 12:00
    # Policy 'run_once' should return the most recent missed run (12:00)
    job = SchedulerJob(
        id="interval_job",
        name="Interval Job",
        schedule=SchedulerJobSchedule(kind="interval", expr="60"),
        command=SchedulerJobCommand(type="python", path="test.py"),
        policy="run_once",
        state=SchedulerJobState(last_run_at=last_run.isoformat())
    )
    next_run = compute_next_run(job, now)
    assert next_run == datetime(2026, 7, 18, 12, 0, 0, tzinfo=ZoneInfo("Europe/Paris"))


def test_next_run_interval_catch_up():
    """Verify compute_next_run with policy 'catch_up' for interval jobs."""
    now = datetime(2026, 7, 18, 12, 0, 0, tzinfo=ZoneInfo("Europe/Paris"))
    last_run = now - timedelta(hours=3) # 9:00
    
    # Missed runs at 10:00, 11:00, 12:00
    # Policy 'catch_up' should return the first chronologically missed run (10:00)
    job = SchedulerJob(
        id="interval_job",
        name="Interval Job",
        schedule=SchedulerJobSchedule(kind="interval", expr="60"),
        command=SchedulerJobCommand(type="python", path="test.py"),
        policy="catch_up",
        state=SchedulerJobState(last_run_at=last_run.isoformat())
    )
    next_run = compute_next_run(job, now)
    assert next_run == datetime(2026, 7, 18, 10, 0, 0, tzinfo=ZoneInfo("Europe/Paris"))


def test_next_run_cron_dst_transition():
    """Verify next run calculation for cron handles DST transitions correctly."""
    # DST transition from Winter to Summer time in Europe/Paris (moves forward 1 hour)
    # Sunday, March 29, 2026 at 2:00 AM -> 3:00 AM
    tz_name = "Europe/Paris"
    
    # Cron scheduled for every hour at minute 30
    # Starting at March 29, 2026, 1:00 AM
    base_time = datetime(2026, 3, 29, 1, 0, 0, tzinfo=ZoneInfo(tz_name))
    
    job = SchedulerJob(
        id="cron_dst",
        name="Cron DST",
        schedule=SchedulerJobSchedule(kind="cron", expr="30 * * * *"),
        command=SchedulerJobCommand(type="python", path="test.py"),
        timezone=tz_name,
        state=SchedulerJobState(last_run_at=base_time.isoformat())
    )
    
    # The first run should be March 29, 2026, 1:30 AM (UTC+1)
    next_run_1 = compute_next_run(job, base_time)
    assert next_run_1 is not None
    assert next_run_1.hour == 1
    assert next_run_1.minute == 30
    assert next_run_1.utcoffset() == timedelta(hours=1)
    
    # The second run should cross the DST transition (2:00 AM becomes 3:00 AM)
    # So 2:30 AM does not exist; next run is March 29, 2026, 3:30 AM (UTC+2)
    job.state.last_run_at = next_run_1.isoformat()
    next_run_2 = compute_next_run(job, next_run_1)
    assert next_run_2 is not None
    assert next_run_2.hour == 3
    assert next_run_2.minute == 30
    assert next_run_2.utcoffset() == timedelta(hours=2)


def test_scheduler_history_idempotency(tmp_path):
    """Verify database run history recording and unique constraint idempotency."""
    db_file = tmp_path / "scheduler.db"
    
    job_id = "daily_launch"
    scheduled_at = "2026-07-18T10:00:00+02:00"
    run_at = datetime.now().isoformat()
    
    # 1. Initialize DB and record first run
    success_1 = scheduler_history.record_run(
        job_id=job_id,
        scheduled_at=scheduled_at,
        run_at=run_at,
        duration=12.4,
        status="ok",
        db_path=db_file
    )
    assert success_1 is True
    
    # Check if marked as completed
    assert scheduler_history.is_run_completed(job_id, scheduled_at, db_path=db_file) is True
    
    # 2. Record second run with same job_id and scheduled_at (idempotency unique key collision)
    success_2 = scheduler_history.record_run(
        job_id=job_id,
        scheduled_at=scheduled_at,
        run_at=run_at,
        duration=5.1,
        status="ok",
        db_path=db_file
    )
    # Must fail due to unique constraint on idempotency key
    assert success_2 is False
