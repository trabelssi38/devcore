from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)

try:
    from croniter import croniter, CroniterBadDateError
    HAS_CRONITER = True
except ImportError:
    HAS_CRONITER = False


MAX_INTERVAL_MINUTES = 525600  # One year; avoid arbitrary/overflowing durations.
MAX_CRON_SEARCH_YEARS = 8


def _interval_minutes(expr: str) -> int:
    if not isinstance(expr, str) or len(expr) > 64:
        raise ValueError('Interval must be 1..525600 integer minutes')
    try:
        value = int(expr)
    except ValueError as exc:
        raise ValueError('Interval must be 1..525600 integer minutes') from exc
    _validate_interval(value)
    return value


def _validate_interval(value: int) -> None:
    if type(value) is not int or not 1 <= value <= MAX_INTERVAL_MINUTES:
        raise ValueError('Interval must be 1..525600 integer minutes')


class SchedulerJobSchedule(BaseModel):
    kind: Literal['cron', 'interval', 'once']
    expr: str = Field(min_length=1, max_length=256)

    @model_validator(mode='after')
    def validate_interval(self):
        if self.kind == 'interval':
            _interval_minutes(self.expr)
        elif self.kind == 'once':
            datetime.fromisoformat(self.expr)
        elif not HAS_CRONITER or not croniter.is_valid(self.expr):
            raise ValueError('Cron requires croniter and a valid expression')
        return self


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
    completed_count: int = Field(default=0, alias="completed", strict=True, ge=0)

    @field_validator('next_run_at', 'last_run_at')
    @classmethod
    def validate_timestamp(cls, value):
        if value is not None:
            if len(value) > 128:
                raise ValueError('Scheduler timestamp too long')
            datetime.fromisoformat(value)
        return value


class SchedulerJob(BaseModel):
    schema_version: int = 1
    id: str
    name: str
    enabled: bool = True
    no_agent: bool = True
    schedule: SchedulerJobSchedule
    command: SchedulerJobCommand
    state: SchedulerJobState = Field(default_factory=SchedulerJobState)
    policy: Literal['skip', 'run_once', 'catch_up'] = 'skip'
    timezone: str = Field(default='Europe/Paris', min_length=1, max_length=128)

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (KeyError, ValueError) as exc:
            raise ValueError('Unknown scheduler timezone') from exc
        return value


def _ensure_aware(dt: datetime, tz_name: str) -> datetime:
    """Ensure a datetime is timezone-aware in the target timezone."""
    tz = ZoneInfo(tz_name)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
    return dt.astimezone(tz)


def get_missed_cron_slots(expr: str, last_run: datetime, now: datetime, tz_name: str, max_lookback_days: int = 30) -> List[datetime]:
    """Get all cron execution slots in the past, between last_run and now."""
    if not HAS_CRONITER:
        raise ValueError('Cron requires croniter')
    tz = ZoneInfo(tz_name)
    last_run_tz = _ensure_aware(last_run, tz_name)
    now_tz = _ensure_aware(now, tz_name)

    # Clamp the starting base time to avoid infinite loop if last_run is way in the past
    clamp_base = now_tz - timedelta(days=max_lookback_days)
    if last_run_tz < clamp_base:
        last_run_tz = clamp_base

    cron = croniter(expr, last_run_tz, max_years_between_matches=MAX_CRON_SEARCH_YEARS)
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
    _validate_interval(interval_minutes)
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
        interval_mins = _interval_minutes(expr)
        delta = timedelta(minutes=interval_mins)

        if job.policy == "skip":
            # Fast forward to next future slot
            if last_run_dt:
                steps = max(1, (now_tz - last_run_dt) // delta + 1)
                return last_run_dt + steps * delta
            else:
                return now_tz + timedelta(minutes=interval_mins)

        elif job.policy == "run_once":
            # If there are missed runs, return the most recent missed one.
            # Otherwise return the next future run.
            # Same 30-day lookback as before, without truncation at 1000 slots.
            bounded_base = max(base_time, now_tz - timedelta(days=30))
            steps = (now_tz - bounded_base) // delta
            if steps >= 1:
                return bounded_base + steps * delta
            return base_time + delta

        elif job.policy == "catch_up":
            # Return the first missed run in the past.
            # If none, return the next future run.
            bounded_base = max(base_time, now_tz - timedelta(days=30))
            first = bounded_base + delta
            if first <= now_tz:
                return first
            return base_time + delta

    elif kind == "cron":
        if not HAS_CRONITER:
            raise ValueError('Cron requires croniter')

        if job.policy == "skip":
            # Fast forward to next cron slot strictly in the future of now
            cron = croniter(expr, now_tz, max_years_between_matches=MAX_CRON_SEARCH_YEARS)
            return cron.get_next(datetime)

        elif job.policy == "run_once":
            bounded_base = max(base_time, now_tz - timedelta(days=30))
            if bounded_base < now_tz:
                # Include a slot exactly at now, without enumerating missed slots.
                cron = croniter(expr, now_tz + timedelta(microseconds=1),
                    max_years_between_matches=MAX_CRON_SEARCH_YEARS)
                try:
                    latest = cron.get_prev(datetime)
                except CroniterBadDateError:
                    latest = None  # No previous slot within the bounded search.
                if latest is not None and bounded_base < latest <= now_tz:
                    return latest
            # No missed slot in the lookback: choose a future occurrence, never
            # one from before the lookback or from a last-run already applied.
            cron = croniter(expr, max(base_time, now_tz), max_years_between_matches=MAX_CRON_SEARCH_YEARS)
            return cron.get_next(datetime)

        elif job.policy == "catch_up":
            missed = get_missed_cron_slots(expr, base_time, now_tz, tz_name)
            if missed:
                return missed[0]
            cron = croniter(expr, base_time, max_years_between_matches=MAX_CRON_SEARCH_YEARS)
            return cron.get_next(datetime)

    return None
