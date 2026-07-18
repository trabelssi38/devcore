from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)

try:
    from croniter import croniter
    HAS_CRONITER = True
except ImportError:
    HAS_CRONITER = False


class SchedulerJobSchedule(BaseModel):
    kind: str  # "cron", "interval", "once"
    expr: str  # e.g., "0 10 * * *", "30" (for minutes), or ISO timestamp


class SchedulerJobCommand(BaseModel):
    type: str  # "powershell", "python"
    path: str
    args: List[str] = Field(default_factory=list)


class SchedulerJobState(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    next_run_at: Optional[str] = None
    last_run_at: Optional[str] = None
    last_status: Optional[str] = None  # "ok", "error", "skipped"
    last_error: Optional[str] = None
    completed_count: int = Field(default=0, alias="completed")


class SchedulerJob(BaseModel):
    schema_version: int = 1
    id: str
    name: str
    enabled: bool = True
    no_agent: bool = True
    schedule: SchedulerJobSchedule
    command: SchedulerJobCommand
    state: SchedulerJobState = Field(default_factory=SchedulerJobState)
    policy: str = "skip"  # "skip", "run_once", "catch_up"
    timezone: str = "Europe/Paris"


def _ensure_aware(dt: datetime, tz_name: str) -> datetime:
    """Ensure a datetime is timezone-aware in the target timezone."""
    tz = ZoneInfo(tz_name)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
    return dt.astimezone(tz)


def get_missed_cron_slots(expr: str, last_run: datetime, now: datetime, tz_name: str, max_lookback_days: int = 30) -> List[datetime]:
    """Get all cron execution slots in the past, between last_run and now."""
    if not HAS_CRONITER:
        return []
    tz = ZoneInfo(tz_name)
    last_run_tz = _ensure_aware(last_run, tz_name)
    now_tz = _ensure_aware(now, tz_name)

    # Clamp the starting base time to avoid infinite loop if last_run is way in the past
    clamp_base = now_tz - timedelta(days=max_lookback_days)
    if last_run_tz < clamp_base:
        last_run_tz = clamp_base

    cron = croniter(expr, last_run_tz)
    slots = []
    # Avoid infinite loops by limiting iterations
    for _ in range(1000):
        nxt = cron.get_next(datetime)
        if nxt <= now_tz:
            slots.append(nxt)
        else:
            break
    return slots


def get_missed_interval_slots(interval_minutes: int, last_run: datetime, now: datetime, tz_name: str, max_lookback_days: int = 30) -> List[datetime]:
    """Get all interval execution slots in the past, between last_run and now."""
    last_run_tz = _ensure_aware(last_run, tz_name)
    now_tz = _ensure_aware(now, tz_name)

    clamp_base = now_tz - timedelta(days=max_lookback_days)
    if last_run_tz < clamp_base:
        last_run_tz = clamp_base

    slots = []
    curr = last_run_tz + timedelta(minutes=interval_minutes)
    # Avoid infinite loops
    for _ in range(1000):
        if curr <= now_tz:
            slots.append(curr)
            curr += timedelta(minutes=interval_minutes)
        else:
            break
    return slots


def compute_next_run(job: SchedulerJob, now: datetime) -> Optional[datetime]:
    """
    Compute the next run time for a job based on its schedule, timezone, policy, and state.
    Returns a timezone-aware datetime in the job's timezone, or None if no more runs are scheduled.
    """
    tz_name = job.timezone
    tz = ZoneInfo(tz_name)
    now_tz = _ensure_aware(now, tz_name)

    kind = job.schedule.kind
    expr = job.schedule.expr

    last_run_dt = None
    if job.state.last_run_at:
        try:
            last_run_dt = _ensure_aware(datetime.fromisoformat(job.state.last_run_at), tz_name)
        except Exception:
            pass

    # Simple base time resolution
    base_time = last_run_dt if last_run_dt else now_tz

    if kind == "once":
        # One-shot job
        try:
            run_at = _ensure_aware(datetime.fromisoformat(expr), tz_name)
            if run_at > now_tz:
                return run_at
            # If in the past, check if it has already run
            if job.state.last_run_at:
                return None
            # If it missed its run but is within a 2-hour grace period, allow it
            if now_tz - run_at <= timedelta(hours=2):
                return run_at
            return None
        except Exception:
            return None

    elif kind == "interval":
        try:
            interval_mins = int(expr)
        except ValueError:
            return None

        if job.policy == "skip":
            # Fast forward to next future slot
            if last_run_dt:
                next_run = last_run_dt + timedelta(minutes=interval_mins)
                while next_run <= now_tz:
                    next_run += timedelta(minutes=interval_mins)
                return next_run
            else:
                return now_tz + timedelta(minutes=interval_mins)

        elif job.policy == "run_once":
            # If there are missed runs, return the most recent missed one.
            # Otherwise return the next future run.
            missed = get_missed_interval_slots(interval_mins, base_time, now_tz, tz_name)
            if missed:
                # Return the most recent missed one
                return missed[-1]
            return base_time + timedelta(minutes=interval_mins)

        elif job.policy == "catch_up":
            # Return the first missed run in the past.
            # If none, return the next future run.
            missed = get_missed_interval_slots(interval_mins, base_time, now_tz, tz_name)
            if missed:
                return missed[0]
            return base_time + timedelta(minutes=interval_mins)

    elif kind == "cron":
        if not HAS_CRONITER:
            logger.warning("croniter is not installed, cannot compute cron next run.")
            return None

        if job.policy == "skip":
            # Fast forward to next cron slot strictly in the future of now
            cron = croniter(expr, now_tz)
            return cron.get_next(datetime)

        elif job.policy == "run_once":
            missed = get_missed_cron_slots(expr, base_time, now_tz, tz_name)
            if missed:
                return missed[-1]
            cron = croniter(expr, base_time)
            return cron.get_next(datetime)

        elif job.policy == "catch_up":
            missed = get_missed_cron_slots(expr, base_time, now_tz, tz_name)
            if missed:
                return missed[0]
            cron = croniter(expr, base_time)
            return cron.get_next(datetime)

    return None
