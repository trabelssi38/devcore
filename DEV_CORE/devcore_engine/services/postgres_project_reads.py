"""Project-scoped context and task-audit reads for the PostgreSQL team profile."""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
from urllib.parse import unquote, urlparse

from devcore_engine.security.identity import AUDIT_READ, CONTEXT_READ, Principal, ProjectAccessDenied

from .project_context import ContextBudgetExceeded, encode_context, load_project_context
from .registered_project_context import ProjectContextUnavailable
from .task_audit import (
    InvalidAuditCursor, MAX_AUDIT_BYTES, QUALIFIED_ACTIONS,
    TaskAuditUnavailable, audit_identifier, project_row, safe_identifier,
)


class PostgresProjectReader:
    def __init__(self, dsn: str):
        parsed = urlparse(dsn.replace("postgresql+pg8000://", "postgresql://", 1))
        if parsed.scheme != "postgresql" or parsed.hostname not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("Project reads require a local PostgreSQL DSN")
        if not parsed.username or not parsed.path or parsed.path == "/":
            raise ValueError("Project reads require a PostgreSQL role and database")
        self._options = dict(
            user=unquote(parsed.username), password=unquote(parsed.password or ""),
            host=parsed.hostname, port=parsed.port or 5432,
            database=parsed.path.lstrip("/"),
        )

    @contextmanager
    def _transaction(self, project: str):
        from devcore_engine.context import validate_project_id
        import pg8000.dbapi

        project = validate_project_id(project)
        connection = pg8000.dbapi.connect(**self._options)
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT set_config('app.current_project_id', %s, true)", (project,))
            yield cursor
            connection.rollback()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def context(self, principal: Principal, *, budget_bytes: int = 12000, query: str = ""):
        if not isinstance(principal, Principal) or principal.action != CONTEXT_READ:
            raise ProjectAccessDenied("Context read principal required")
        try:
            with self._transaction(principal.project_id) as cursor:
                cursor.execute("SELECT root_path FROM projects WHERE id=%s AND status='active'",
                               (principal.project_id,))
                row = cursor.fetchone()
            if row is None or not isinstance(row[0], str) or not row[0].strip():
                raise ValueError("Registered project root required")
            root = Path(row[0])
            if not root.is_absolute() or not root.is_dir():
                raise ValueError("Existing absolute registered root required")
            root = root.resolve()
            directory = (root / "docs" / "project-context").resolve()
            if not directory.is_relative_to(root) or not directory.is_dir():
                raise ValueError("Context must be inside registered root")
            return load_project_context(directory, principal.project_id,
                                        budget_bytes=budget_bytes, query=query)
        except ContextBudgetExceeded:
            raise
        except Exception as exc:
            raise ProjectContextUnavailable("Registered project context unavailable") from exc

    def task_audit(self, principal: Principal, *, limit: int = 20,
                   before_id: str | None = None, task_id: str | None = None) -> dict:
        if not isinstance(principal, Principal) or principal.action != AUDIT_READ:
            raise ProjectAccessDenied("Task audit principal required")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Audit limit must be 1..100")
        if before_id is not None:
            try:
                audit_identifier(before_id)
            except (ValueError, TypeError, AttributeError) as exc:
                raise InvalidAuditCursor("Invalid scoped audit cursor") from exc
        if task_id is not None:
            safe_identifier(task_id)
        try:
            project = principal.project_id
            with self._transaction(project) as cursor:
                where = "a.project_id=%s AND a.entity_type='task' AND a.action IN ('task.complete','task.delete','task.pause','task.resume')"
                values: list = [project]
                if task_id is not None:
                    where += " AND a.entity_id=%s"
                    values.append(task_id)
                if before_id is not None:
                    cursor.execute("""SELECT created_at,id FROM audit_log
                        WHERE project_id=%s AND entity_type='task'
                        AND action IN ('task.complete','task.delete','task.pause','task.resume')
                        AND id=%s""" + (" AND entity_id=%s" if task_id else ""),
                        (project, before_id, task_id) if task_id else (project, before_id))
                    boundary = cursor.fetchone()
                    if boundary is None:
                        raise InvalidAuditCursor("Invalid scoped audit cursor")
                    where += " AND (a.created_at,a.id)<(%s,%s)"
                    values.extend(boundary)
                cursor.execute("""SELECT a.id,a.project_id,a.entity_id,a.actor,a.action,
                    a.entity_type,a.created_at,a.details,t.legacy_id,t.task_uuid
                    FROM audit_log a JOIN tasks t ON t.task_uuid=a.task_uuid
                        AND t.project_id=a.project_id
                    WHERE """ + where + " ORDER BY a.created_at DESC,a.id DESC LIMIT %s",
                    (*values, limit + 1))
                rows = cursor.fetchall()
            result = {"success": True, "project": project, "events": [],
                      "supported_actions": list(QUALIFIED_ACTIONS),
                      "next_before_id": None, "has_more": len(rows) > limit}
            for row in rows[:limit]:
                identifier, row_project, entity, actor, action, kind, created, details, legacy, task_uuid = row
                if entity != (legacy or str(task_uuid)):
                    raise ValueError("Invalid audit task association")
                projected = project_row({
                    "id": identifier, "project_id": row_project, "task_id": entity,
                    "entity_id": entity, "actor": actor, "action": action,
                    "entity_type": kind, "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
                    "details": json.dumps(details) if isinstance(details, dict) else details,
                }, project)
                result["events"].append(projected)
                result["next_before_id"] = projected["id"] if result["has_more"] else None
                bounded = {**result, "has_more": True, "next_before_id": projected["id"]}
                if len((encode_context(bounded) + "\n").encode("utf-8")) > MAX_AUDIT_BYTES:
                    result["events"].pop()
                    if not result["events"]:
                        raise ValueError("Audit row exceeds response bound")
                    result["has_more"] = True
                    result["next_before_id"] = result["events"][-1]["id"]
                    break
            if len((encode_context(result) + "\n").encode("utf-8")) > MAX_AUDIT_BYTES:
                raise ValueError("Audit envelope exceeds response bound")
            return result
        except InvalidAuditCursor:
            raise
        except Exception as exc:
            raise TaskAuditUnavailable("Qualified task audit unavailable") from exc
