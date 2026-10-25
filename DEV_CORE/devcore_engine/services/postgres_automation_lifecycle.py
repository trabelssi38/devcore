"""Authenticated, project-scoped team hook operations with no task mutation."""

from __future__ import annotations

import re
import subprocess

from devcore_engine.security.identity import Principal, ProjectAccessDenied, WRITE

from .postgres_automation_hooks import PostgresAutomationHooks, TOKEN, _principal


COMMIT = re.compile(r"^[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?$")
SOURCES = frozenset({"codex", "claude", "gemini", "git"})
TOOL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")


class HookOperationFailed(RuntimeError):
    def __init__(self, event_id: str, code: str):
        super().__init__(code)
        self.event_id = event_id
        self.code = code


class PostgresAutomationLifecycle(PostgresAutomationHooks):
    """Persist verified reads and Git evidence, never infer task transitions."""

    def _task_snapshot(self, project: str, *, since=None) -> dict:
        with self._transaction(project) as cursor:
            cursor.execute("""SELECT count(*),count(*) FILTER (WHERE status='done'),
                count(*) FILTER (WHERE status NOT IN ('done','deleted','skipped'))
                FROM tasks WHERE project_id=%s AND status<>'deleted'""", (project,))
            total, done, open_count = cursor.fetchone()
            cursor.execute("""SELECT coalesce(legacy_id,task_uuid::text),title,status
                FROM tasks WHERE project_id=%s AND status='active'
                ORDER BY updated_at DESC,task_number LIMIT 1""", (project,))
            active = cursor.fetchone()
            result = {"tasks_total": total, "tasks_done": done,
                      "tasks_open": open_count,
                      "active_task": ({"id": active[0], "title": active[1][:200],
                                       "status": active[2]} if active else None)}
            if since is not None:
                cursor.execute("""SELECT count(*) FROM tasks WHERE project_id=%s
                    AND status='done' AND completed_at >= %s""", (project, since))
                result["tasks_completed_since_start"] = cursor.fetchone()[0]
            return result

    def _session_start_time(self, project: str, actor: str, source: str, session: str):
        with self._transaction(project) as cursor:
            cursor.execute("""SELECT created_at FROM automation_hook_events
                WHERE project_id=%s AND actor=%s AND hook='session_start'
                AND source=%s AND idempotency_key=%s AND status='succeeded'""",
                (project, actor, source, f"session:{session}:start"))
            row = cursor.fetchone()
            return row[0] if row else None

    def _git_commit(self, project: str, sha: str) -> dict:
        with self._transaction(project) as cursor:
            cursor.execute("SELECT root_path FROM projects WHERE id=%s AND status='active'", (project,))
            row = cursor.fetchone()
        if row is None:
            raise ProjectAccessDenied("Active registered project required")
        root = row[0]
        try:
            resolved = subprocess.run(["git", "-C", root, "rev-parse", "--verify", f"{sha}^{{commit}}"],
                                      capture_output=True, text=True, timeout=10, check=False)
            reachable = subprocess.run(["git", "-C", root, "merge-base", "--is-ancestor", sha, "HEAD"],
                                       capture_output=True, timeout=10, check=False)
            if resolved.returncode != 0 or reachable.returncode != 0:
                raise ValueError("Commit is not reachable from registered repository HEAD")
            return {"commit": resolved.stdout.strip().lower(), "verified": "git_reachable"}
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError("Git verification unavailable") from exc

    def execute(self, principal: Principal, project: str, hook: str, source: str,
                *, session: str | None = None, commit: str | None = None,
                tool: str | None = None, reported_outcome: str | None = None,
                occurrence: str | None = None) -> dict:
        actor = _principal(principal, project, WRITE)
        if source not in SOURCES:
            raise ValueError("Known hook source required")
        if hook in {"session_start", "session_end"}:
            if source == "git" or not isinstance(session, str) or TOKEN.fullmatch(session) is None:
                raise ValueError("Bounded client session ID required")
            key = f"session:{session}:{'start' if hook == 'session_start' else 'end'}"
            if len(key) > 160:
                raise ValueError("Session ID too long")
            details = {"session": session}
        elif hook == "git_commit":
            if source != "git" or not isinstance(commit, str) or COMMIT.fullmatch(commit) is None:
                raise ValueError("Full Git commit SHA required")
            key = f"commit:{commit.lower()}"
            details = {"commit": commit.lower()}
        elif hook == "tool_use":
            if (source == "git" or not isinstance(session, str) or TOKEN.fullmatch(session) is None
                    or not isinstance(tool, str) or TOOL.fullmatch(tool) is None
                    or reported_outcome not in {"succeeded", "failed"}
                    or not isinstance(occurrence, str) or TOKEN.fullmatch(occurrence) is None):
                raise ValueError("Bounded tool report required")
            key = f"tool:{occurrence}"
            if len(key) > 160:
                raise ValueError("Tool report key too long")
            details = {"session": session, "tool": tool, "occurrence": occurrence,
                       "reported_outcome": reported_outcome,
                       "verification": "client_report_only"}
        else:
            raise ValueError("Unknown hook")
        details["source_verification"] = "authenticated_client_declaration"
        event_id, created = self.start(principal, project, hook, source, key,
                                       details, correlation_id=session)
        if not created:
            return {"created": False, "event": self.own_event(principal, project, event_id)}
        try:
            if hook == "session_start":
                result = self._task_snapshot(project)
                result["context_url"] = f"/api/v1/project/context?project={project}"
            elif hook == "session_end":
                since = self._session_start_time(project, actor, source, session)
                if since is None:
                    raise HookOperationFailed(event_id, "session_start_missing")
                result = self._task_snapshot(project, since=since)
                result["metrics_source"] = "project_tasks_since_session_start"
            elif hook == "git_commit":
                result = self._git_commit(project, commit)
            else:
                result = {"verification": "client_report_only"}
            self.finish(principal, project, event_id, "succeeded", result=result)
        except HookOperationFailed:
            self.finish(principal, project, event_id, "failed", error="session_start_missing")
            raise
        except ValueError as exc:
            self.finish(principal, project, event_id, "failed", error="verification_failed")
            raise HookOperationFailed(event_id, "verification_failed") from exc
        except Exception:
            self.finish(principal, project, event_id, "failed", error="source_unavailable")
            raise
        return {"created": True, "event": self.own_event(principal, project, event_id)}
