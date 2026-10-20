"""Persist qualified hook outcomes; never execute a legacy hook or job."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from uuid import uuid4

from devcore_engine.context import validate_project_id
from devcore_engine.runs.postgres_store import PostgresRunStore
from devcore_engine.security.identity import Principal, READ, WRITE, ProjectAccessDenied


HOOKS = frozenset({"session_start", "session_end", "git_commit", "tool_use"})
RESULTS = frozenset({"succeeded", "failed"})
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")
ERROR_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")


def _principal(principal: Principal, project: str, action: str) -> str:
    project = validate_project_id(project)
    if (not isinstance(principal, Principal) or principal.project_id != project
            or principal.action != action or not principal.user_id.strip()):
        raise ProjectAccessDenied("Authorized project principal required")
    return principal.user_id


def _registered_git_root(raw: str) -> bool:
    if not isinstance(raw, str) or not raw.strip():
        return False
    root = Path(raw)
    if not root.is_absolute() or not root.is_dir():
        return False
    try:
        result = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                                capture_output=True, text=True, timeout=10, check=False)
        return result.returncode == 0 and Path(result.stdout.strip()).resolve() == root.resolve()
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False


class PostgresAutomationHooks(PostgresRunStore):
    """Store hook attempts under transaction-local project RLS."""

    def verify_ready(self) -> None:
        with self._transaction("devcore") as cursor:
            cursor.execute("""SELECT r.rolsuper,r.rolbypassrls,
                (SELECT relrowsecurity AND relforcerowsecurity FROM pg_class
                 WHERE oid='automation_hook_events'::regclass)
                FROM pg_roles r WHERE r.rolname=current_user""")
            flags = cursor.fetchone()
            if flags is None or flags[0] or flags[1] or not flags[2]:
                raise RuntimeError("Automation hook role or RLS is unsafe")
            cursor.execute("""SELECT 1 FROM pg_policies WHERE schemaname='public'
                AND tablename='automation_hook_events'
                AND policyname='rls_automation_hook_events_project_isolation'""")
            if cursor.fetchone() is None:
                raise RuntimeError("Automation hook RLS policy is missing")

    def start(self, principal: Principal, project: str, hook: str, source: str,
              idempotency_key: str, details: dict | None = None,
              correlation_id: str | None = None) -> tuple[str, bool]:
        actor = _principal(principal, project, WRITE)
        if hook not in HOOKS:
            raise ValueError("Unknown automation hook")
        if (not isinstance(source, str) or not 1 <= len(source) <= 80
                or not isinstance(idempotency_key, str)
                or TOKEN.fullmatch(idempotency_key) is None):
            raise ValueError("Bounded source and idempotency key required")
        if correlation_id is not None and (not isinstance(correlation_id, str)
                                           or len(correlation_id) > 128):
            raise ValueError("Bounded correlation ID required")
        if details is None:
            details = {}
        if not isinstance(details, dict):
            raise ValueError("Bounded details object required")
        encoded = json.dumps(details, ensure_ascii=False)
        if len(encoded.encode("utf-8")) > 8192:
            raise ValueError("Bounded details object required")
        event_id = "hook-" + uuid4().hex
        with self._transaction(project) as cursor:
            cursor.execute("""SELECT root_path FROM projects
                WHERE id=%s AND status='active'""", (project,))
            registered = cursor.fetchone()
            if registered is None or not _registered_git_root(registered[0]):
                raise ProjectAccessDenied("Active registered Git project required")
            cursor.execute("""INSERT INTO automation_hook_events
                (id,project_id,actor,hook,source,correlation_id,idempotency_key,status,details)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'running',%s::jsonb)
                ON CONFLICT (project_id,idempotency_key) DO NOTHING RETURNING id""",
                (event_id, project, actor, hook, source, correlation_id,
                 idempotency_key, encoded))
            inserted = cursor.fetchone()
            if inserted is not None:
                return inserted[0], True
            cursor.execute("""SELECT id,actor,hook,source FROM automation_hook_events
                WHERE project_id=%s AND idempotency_key=%s""",
                (project, idempotency_key))
            existing = cursor.fetchone()
            if existing is None:
                raise RuntimeError("Automation hook conflict was not visible")
            if tuple(existing[1:]) != (actor, hook, source):
                raise ProjectAccessDenied("Automation key belongs to a different origin")
            return existing[0], False

    def finish(self, principal: Principal, project: str, event_id: str,
               status: str, error: str | None = None,
               result: dict | None = None) -> bool:
        actor = _principal(principal, project, WRITE)
        if status not in RESULTS or not isinstance(event_id, str) or not event_id.startswith("hook-"):
            raise ValueError("Invalid terminal automation result")
        if error is not None and (not isinstance(error, str)
                                  or ERROR_CODE.fullmatch(error) is None):
            raise ValueError("Bounded error code required")
        if result is None:
            result = {}
        if not isinstance(result, dict):
            raise ValueError("Bounded result object required")
        with self._transaction(project) as cursor:
            cursor.execute("""SELECT details FROM automation_hook_events WHERE project_id=%s
                AND id=%s AND actor=%s AND status='running' FOR UPDATE""",
                (project, event_id, actor))
            current = cursor.fetchone()
            if current is None:
                return False
            details = current[0] if isinstance(current[0], dict) else json.loads(current[0])
            merged = {**details, **result}
            encoded = json.dumps(merged, ensure_ascii=False)
            if len(encoded.encode("utf-8")) > 8192:
                raise ValueError("Bounded result object required")
            cursor.execute("""UPDATE automation_hook_events SET status=%s,
                error=%s,details=%s::jsonb,finished_at=now() WHERE project_id=%s AND id=%s
                AND actor=%s AND status='running' RETURNING id""",
                (status, error, encoded, project, event_id, actor))
            return cursor.fetchone() is not None

    def own_event(self, principal: Principal, project: str, event_id: str) -> dict | None:
        actor = _principal(principal, project, WRITE)
        with self._transaction(project) as cursor:
            cursor.execute("""SELECT id,hook,source,status,error,details,created_at,finished_at
                FROM automation_hook_events WHERE project_id=%s AND id=%s AND actor=%s""",
                (project, event_id, actor))
            row = cursor.fetchone()
            if row is None:
                return None
            record = dict(zip(("id", "hook", "source", "status", "error", "details",
                               "created_at", "finished_at"), row))
            if isinstance(record["details"], str):
                record["details"] = json.loads(record["details"])
            return record

    def recent(self, principal: Principal, project: str, *, limit: int = 20) -> list[dict]:
        _principal(principal, project, READ)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Limit must be 1..100")
        with self._transaction(project) as cursor:
            cursor.execute("""SELECT id,actor,hook,source,correlation_id,status,error,details,created_at,finished_at
                FROM automation_hook_events WHERE project_id=%s
                ORDER BY created_at DESC,id DESC LIMIT %s""", (project, limit))
            results = [dict(zip(("id", "actor", "hook", "source", "correlation_id",
                                 "status", "error", "details", "created_at", "finished_at"), row))
                       for row in cursor.fetchall()]
            for result in results:
                if isinstance(result["details"], str):
                    result["details"] = json.loads(result["details"])
            return results
