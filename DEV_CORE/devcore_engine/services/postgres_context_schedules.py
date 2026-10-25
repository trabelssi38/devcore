"""Project-scoped enrollment for verifiable context snapshots."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import sys
from zoneinfo import ZoneInfo

from croniter import croniter

from devcore_engine.runs.postgres_schedules import CONTEXT_SCRIPT
from devcore_engine.runs.postgres_store import PostgresRunStore
from devcore_engine.security.identity import Principal, ProjectAccessDenied, WRITE

from .postgres_automation_hooks import _principal, _registered_git_root


class PostgresContextSchedules(PostgresRunStore):
    def register(self, principal: Principal, project: str, *, timezone: str,
                 hour: int, minute: int) -> dict:
        actor = _principal(principal, project, WRITE)
        if (not isinstance(timezone, str) or len(timezone) > 80
                or type(hour) is not int or not 0 <= hour <= 23
                or type(minute) is not int or not 0 <= minute <= 59):
            raise ValueError("Explicit timezone and local time required")
        zone = ZoneInfo(timezone)
        expression = f"{minute} {hour} * * *"
        next_due = croniter(expression, datetime.now(UTC).astimezone(zone)).get_next(datetime).astimezone(UTC)
        schedule_id = f"schedule-context-refresh-{project}"
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
                    raise ValueError("Context schedule already exists with different configuration")
                return {"project": project, "schedule_id": schedule_id, "created": False}
            metadata = {"execution_ready": True, "job_kind": "context_refresh",
                        "command": [sys._base_executable, str(CONTEXT_SCRIPT),
                                    "--project", project, "--root", str(row[0])],
                        "timeout_seconds": 60, "created_by": actor}
            cursor.execute("""INSERT INTO schedules
                (id,project_id,name,cron,timezone,status,next_run_at,metadata)
                VALUES (%s,%s,'Project context facts',%s,%s,'active',%s,%s::jsonb)""",
                (schedule_id, project, expression, timezone, next_due, json.dumps(metadata)))
            return {"project": project, "schedule_id": schedule_id,
                    "created": True, "next_run_at": next_due.isoformat()}
