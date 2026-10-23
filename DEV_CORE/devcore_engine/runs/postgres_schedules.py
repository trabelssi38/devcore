"""Project-scoped PostgreSQL cron dispatch into durable runs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4
from zoneinfo import ZoneInfo

from croniter import croniter

from .postgres_store import PostgresRunStore


DAILY_SCRIPT = Path(__file__).resolve().parents[2] / "Scripts" / "team_daily_metrics_job.py"
CONTEXT_SCRIPT = Path(__file__).resolve().parents[2] / "Scripts" / "team_context_refresh_job.py"


class PostgresScheduleDispatcher(PostgresRunStore):
    """Submit at most one due occurrence per schedule; missed slots are skipped."""

    def verify_ready(self) -> None:
        super().verify_ready()
        with self._transaction("devcore") as cursor:
            cursor.execute("""SELECT r.rolsuper,r.rolbypassrls,
                (SELECT relrowsecurity AND relforcerowsecurity FROM pg_class
                 WHERE oid='schedules'::regclass),
                (SELECT relrowsecurity AND relforcerowsecurity FROM pg_class
                 WHERE oid='schedule_history'::regclass)
                FROM pg_roles r WHERE r.rolname=current_user""")
            flags = cursor.fetchone()
            if flags is None or flags[0] or flags[1] or not flags[2] or not flags[3]:
                raise RuntimeError("PostgreSQL schedule role or RLS is unsafe")
            cursor.execute("""SELECT tablename,policyname FROM pg_policies
                WHERE schemaname='public' AND tablename IN ('schedules','schedule_history')""")
            policies = {tuple(row) for row in cursor.fetchall()}
            if not {("schedules", "rls_schedules_project_isolation"),
                    ("schedule_history", "rls_schedule_history_project_isolation")} <= policies:
                raise RuntimeError("PostgreSQL schedule isolation policies are missing")
            cursor.execute("SELECT id FROM schedules LIMIT 0")
            cursor.execute("SELECT id FROM schedule_history LIMIT 0")
        for project in self._projects():
            with self._transaction(project) as cursor:
                cursor.execute("""SELECT id,cron,timezone,next_run_at,metadata
                    FROM schedules WHERE project_id=%s AND status='active'""", (project,))
                for schedule_id, expression, timezone, due, metadata in cursor.fetchall():
                    if due is None:
                        raise RuntimeError(f"Active schedule {schedule_id} has no next run")
                    self._qualified_command(expression, timezone, metadata)

    @staticmethod
    def _qualified_command(expression: str, timezone: str, metadata: dict) -> tuple[list[str], float, ZoneInfo]:
        if not isinstance(metadata, dict) or metadata.get("execution_ready") is not True:
            raise RuntimeError("Active schedule lacks explicit execution qualification")
        command = metadata.get("command")
        if (not isinstance(command, list) or not 1 <= len(command) <= 32
                or any(not isinstance(part, str) or not 1 <= len(part) <= 4096 for part in command)
                or sum(len(part) for part in command) > 16384):
            raise ValueError("Qualified schedule requires an argv command")
        # The installed venv launcher supervises with its base interpreter.
        # Accept only these two identities for this exact managed script.
        trusted_pythons = {sys.executable, sys._base_executable}
        if (metadata.get("job_kind") == "daily_metrics"
                and (len(command) != 2 or command[0] not in trusted_pythons
                     or command[1] != str(DAILY_SCRIPT))):
            raise ValueError("Daily metrics requires the managed argv command")
        if (metadata.get("job_kind") == "context_refresh"
                and (len(command) != 6 or command[0] not in trusted_pythons
                     or command[1] != str(CONTEXT_SCRIPT)
                     or command[2] != "--project" or command[4] != "--root")):
            raise ValueError("Context refresh requires the managed argv command")
        timeout = metadata.get("timeout_seconds", 300)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 3600:
            raise ValueError("Invalid schedule timeout")
        if (not isinstance(expression, str) or len(expression.split()) != 5
                or not croniter.is_valid(expression)):
            raise ValueError("Invalid schedule cron")
        return command, float(timeout), ZoneInfo(timezone)

    @staticmethod
    def _daily_snapshot(cursor, project: str, day: str, timezone: str) -> dict:
        cursor.execute("""SELECT count(*) FILTER (WHERE (created_at AT TIME ZONE %s)::date=%s::date),
            count(*) FILTER (WHERE (completed_at AT TIME ZONE %s)::date=%s::date)
            FROM tasks WHERE project_id=%s""", (timezone, day, timezone, day, project))
        created, completed = cursor.fetchone()
        cursor.execute("""SELECT count(*) FILTER (WHERE status='succeeded'),
            count(*) FILTER (WHERE status IN ('failed','timed_out'))
            FROM runs WHERE project_id=%s AND (finished_at AT TIME ZONE %s)::date=%s::date""",
            (project, timezone, day))
        succeeded, failed = cursor.fetchone()
        return {"tasks_created": created, "tasks_completed": completed,
                "runs_succeeded": succeeded, "runs_failed": failed}

    def poll_once(self, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("Aware UTC timestamp required")
        now = now.astimezone(UTC)
        dispatched: list[dict] = []
        for project in self._projects():
            with self._transaction(project) as cursor:
                cursor.execute("""SELECT id FROM schedules WHERE project_id=%s
                    AND status='active' AND next_run_at<=%s
                    ORDER BY next_run_at,id LIMIT 20""", (project, now))
                due_ids = [row[0] for row in cursor.fetchall()]
            for schedule_id in due_ids:
                result = self._dispatch_one(project, schedule_id, now)
                if result is not None:
                    dispatched.append(result)
        return dispatched

    def _dispatch_one(self, project: str, schedule_id: str, now: datetime) -> dict | None:
        with self._transaction(project) as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("schedule:" + project,))
            cursor.execute("""SELECT name,cron,timezone,next_run_at,metadata FROM schedules
                WHERE project_id=%s AND id=%s AND status='active' AND next_run_at<=%s
                FOR UPDATE SKIP LOCKED""", (project, schedule_id, now))
            row = cursor.fetchone()
            if row is None:
                return None
            name, expression, timezone, scheduled, metadata = row
            command, timeout, zone = self._qualified_command(expression, timezone, metadata)
            next_due = croniter(expression, now.astimezone(zone)).get_next(datetime).astimezone(UTC)
            key = f"schedule:{schedule_id}:{scheduled.astimezone(UTC).isoformat()}"
            cursor.execute("""SELECT count(*) FROM runs WHERE project_id=%s
                AND metadata->>'schedule_id'=%s AND execution_ready
                AND status IN ('queued','running','paused','waiting_approval')""",
                (project, schedule_id))
            if cursor.fetchone()[0] > 0:
                cursor.execute("""UPDATE schedules SET last_run_at=%s,next_run_at=%s,
                    updated_at=now() WHERE project_id=%s AND id=%s""",
                    (scheduled, next_due, project, schedule_id))
                cursor.execute("""INSERT INTO schedule_history
                    (id,schedule_id,event_type,status,details)
                    VALUES (%s,%s,'overlap','skipped',%s::jsonb)
                    ON CONFLICT (id) DO NOTHING""",
                    ("schedule-overlap-" + hashlib.sha256(key.encode()).hexdigest()[:32],
                     schedule_id, json.dumps({"scheduled_at": scheduled.isoformat()})))
                return {"project": project, "schedule_id": schedule_id,
                        "status": "skipped_overlap", "next_run_at": next_due.isoformat()}
            job_kind = metadata.get("job_kind")
            if job_kind == "daily_metrics":
                from devcore_engine.services.postgres_automation_hooks import _registered_git_root
                cursor.execute("SELECT root_path FROM projects WHERE id=%s AND status='active'", (project,))
                registered = cursor.fetchone()
                if registered is None or not _registered_git_root(registered[0]):
                    raise ValueError("Daily metrics requires a registered Git project")
                day = (scheduled.astimezone(zone).date() - timedelta(days=1)).isoformat()
                snapshot = self._daily_snapshot(cursor, project, day, timezone)
                command = [*command, "--project", project, "--day", day,
                           "--snapshot-json", json.dumps(snapshot, separators=(",", ":"))]
            elif job_kind == "context_refresh":
                from devcore_engine.services.postgres_automation_hooks import _registered_git_root
                cursor.execute("SELECT root_path FROM projects WHERE id=%s AND status='active'", (project,))
                registered = cursor.fetchone()
                if registered is None or not _registered_git_root(registered[0]):
                    raise ValueError("Context refresh requires a registered Git project")
                if command[3] != project or Path(command[5]).resolve() != Path(registered[0]).resolve():
                    raise ValueError("Context refresh command differs from registered project")
            cursor.execute("""SELECT count(*) FROM runs WHERE project_id=%s
                AND status='queued' AND execution_ready""", (project,))
            if cursor.fetchone()[0] >= 50:
                return None
            run_id = "run-" + uuid4().hex[:12]
            cursor.execute("""INSERT INTO runs
                (id,project_id,title,status,command,timeout_seconds,attempt_number,
                 max_attempts,cancellation_requested,idempotency_key,actor,env,metadata,
                 execution_ready)
                VALUES (%s,%s,%s,'queued',%s::jsonb,%s,0,3,false,%s,'scheduler',
                        '{}'::jsonb,%s::jsonb,true)
                ON CONFLICT DO NOTHING RETURNING id""",
                (run_id, project, name, json.dumps(command), float(timeout), key,
                 json.dumps({"schedule_id": schedule_id, "scheduled_at": scheduled.isoformat(),
                             "job_kind": job_kind})))
            inserted = cursor.fetchone()
            if inserted is None:
                cursor.execute("SELECT id FROM runs WHERE project_id=%s AND idempotency_key=%s",
                               (project, key))
                existing = cursor.fetchone()
                if existing is None:
                    raise RuntimeError("Schedule run idempotency conflict")
                run_id = existing[0]
            cursor.execute("""UPDATE schedules SET last_run_at=%s,next_run_at=%s,
                updated_at=now() WHERE project_id=%s AND id=%s""",
                (scheduled, next_due, project, schedule_id))
            history_id = "schedule-" + hashlib.sha256(key.encode()).hexdigest()[:32]
            cursor.execute("""INSERT INTO schedule_history
                (id,schedule_id,run_id,event_type,status,details)
                VALUES (%s,%s,%s,'dispatched','queued',%s::jsonb)
                ON CONFLICT (id) DO NOTHING""",
                (history_id, schedule_id, run_id,
                 json.dumps({"scheduled_at": scheduled.isoformat()})))
            return {"project": project, "schedule_id": schedule_id,
                    "run_id": run_id, "next_run_at": next_due.isoformat()}
