"""Explicit per-project daily metrics enrollment; no legacy daily notes."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter

from devcore_engine.runs.postgres_schedules import DAILY_SCRIPT
from devcore_engine.runs.postgres_store import PostgresRunStore
from devcore_engine.security.identity import Principal, ProjectAccessDenied, WRITE

from .postgres_automation_hooks import _principal, _registered_git_root


class PostgresDailyMetricsSchedules(PostgresRunStore):
    def register(self, principal: Principal, project: str, *, timezone: str,
                 hour: int, minute: int) -> dict:
        actor = _principal(principal, project, WRITE)
        if (not isinstance(timezone, str) or len(timezone) > 80
                or type(hour) is not int or not 0 <= hour <= 23
                or type(minute) is not int or not 0 <= minute <= 59):
            raise ValueError("Explicit timezone and local time required")
        try:
            zone = ZoneInfo(timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Known IANA timezone required") from exc
        expression = f"{minute} {hour} * * *"
        next_due = croniter(expression, datetime.now(UTC).astimezone(zone)).get_next(datetime).astimezone(UTC)
        schedule_id = f"schedule-daily-metrics-{project}"
        with self._transaction(project) as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (schedule_id,))
            cursor.execute("SELECT root_path FROM projects WHERE id=%s AND status='active'", (project,))
            row = cursor.fetchone()
            if row is None or not _registered_git_root(row[0]):
                raise ProjectAccessDenied("Active registered Git project required")
            cursor.execute("SELECT cron,timezone,status FROM schedules WHERE id=%s AND project_id=%s",
                           (schedule_id, project))
            existing = cursor.fetchone()
            if existing is not None:
                if tuple(existing) != (expression, timezone, "active"):
                    raise ValueError("Daily schedule already exists with different configuration")
                return {"project": project, "schedule_id": schedule_id,
                        "status": "active", "created": False}
            metadata = {"execution_ready": True, "job_kind": "daily_metrics",
                        "command": [sys.executable, str(DAILY_SCRIPT)],
                        "timeout_seconds": 30, "created_by": actor}
            cursor.execute("""INSERT INTO schedules
                (id,project_id,name,cron,timezone,status,next_run_at,metadata)
                VALUES (%s,%s,'Daily project metrics',%s,%s,'active',%s,%s::jsonb)""",
                (schedule_id, project, expression, timezone, next_due, json.dumps(metadata)))
            return {"project": project, "schedule_id": schedule_id,
                    "status": "active", "created": True, "next_run_at": next_due.isoformat()}

    def disable(self, principal: Principal, project: str) -> dict:
        _principal(principal, project, WRITE)
        schedule_id = f"schedule-daily-metrics-{project}"
        with self._transaction(project) as cursor:
            cursor.execute("""UPDATE schedules SET status='disabled',updated_at=now()
                WHERE project_id=%s AND id=%s AND status='active' RETURNING id""",
                (project, schedule_id))
            if cursor.fetchone() is None:
                raise ValueError("Active daily schedule not found")
            return {"project": project, "schedule_id": schedule_id, "status": "disabled"}
