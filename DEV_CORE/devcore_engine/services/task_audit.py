"""Read a bounded projection of qualified task mutations after project admission.

No initialization, migration, raw audit details, global fallback or client DB.
The HTTP adapter authenticates the principal. OS-local callers remain trusted.
"""

from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
from uuid import UUID

from devcore_engine.security.identity import AUDIT_READ, Principal, ProjectAccessDenied
from .project_context import encode_context

MAX_AUDIT_BYTES = 65536
QUALIFIED_ACTIONS = ("task.complete", "task.delete", "task.pause", "task.resume")
STATUSES = {"todo", "in_progress", "paused", "done", "blocked", "deleted"}


class TaskAuditUnavailable(RuntimeError):
    pass


class InvalidAuditCursor(ValueError):
    pass


def safe_identifier(value):
    if (not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value)
            or ".." in value):
        raise ValueError("Invalid identifier")
    return value


def audit_identifier(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError("Canonical audit UUID required")
    return value


def project_row(row, project):
    if row["project_id"] != project or row["entity_type"] != "task" or row["entity_id"] != row["task_id"]:
        raise ValueError("Invalid audit association")
    identifier = audit_identifier(row["id"])
    task_id = safe_identifier(row["task_id"])
    actor = row["actor"]
    if (not isinstance(actor, str) or not actor.strip() or len(actor) > 128
            or any(ord(c) < 32 or ord(c) == 127 for c in actor)):
        raise ValueError("Invalid audit actor")
    created = row["created_at"]
    if not isinstance(created, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", created):
        raise ValueError("Invalid audit timestamp")
    details = json.loads(row["details"])
    if not isinstance(details, dict) or type(details.get("schema_version")) is not int or details["schema_version"] != 1:
        raise ValueError("Qualified audit schema required")
    states = {}
    for name in ("before", "after"):
        value = details.get(name)
        if (not isinstance(value, dict) or value.get("status") not in STATUSES
                or type(value.get("version")) is not int or not 1 <= value["version"] <= 9223372036854775807):
            raise ValueError("Invalid audited state")
        states[name] = {"status": value["status"], "version": value["version"]}
    target = {"task.complete": "done", "task.delete": "deleted",
              "task.pause": "paused", "task.resume": "in_progress"}[row["action"]]
    source = {"task.pause": "in_progress", "task.resume": "paused"}.get(row["action"])
    if source is not None and states["before"]["status"] != source:
        raise ValueError("Invalid audited transition")
    if states["after"]["status"] != target or states["after"]["version"] != states["before"]["version"] + 1:
        raise ValueError("Invalid audited mutation")
    return {"id": identifier, "project": project, "task_id": task_id, "actor": actor,
            "action": row["action"], "created_at": created, **states}


def read_task_audit(db_path, principal, *, limit=20, before_id=None, task_id=None):
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
        path = Path(db_path)
        if not path.is_absolute():
            raise ValueError("Explicit server database required")
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=1)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only=ON")
            where = "project_id=? AND action IN (" + ",".join("?" for _ in QUALIFIED_ACTIONS) + ") AND entity_type='task'"
            values = [principal.project_id, *QUALIFIED_ACTIONS]
            if task_id is not None:
                where += " AND task_id=?"
                values.append(task_id)
            if before_id is not None:
                cursor = conn.execute("SELECT rowid FROM audit_log WHERE " + where + " AND id=?",
                                      [*values, before_id]).fetchone()
                if cursor is None:
                    raise InvalidAuditCursor("Invalid scoped audit cursor")
                where += " AND rowid<?"
                values.append(cursor[0])
            # Bound fields before fetching; malformed qualified rows fail the page closed.
            rows = conn.execute("SELECT substr(id,1,37) AS id,project_id,substr(task_id,1,129) AS task_id,"
                "substr(actor,1,129) AS actor,action,entity_type,substr(entity_id,1,129) AS entity_id,"
                "substr(created_at,1,65) AS created_at,substr(details,1,8193) AS details FROM audit_log WHERE "
                + where + " ORDER BY rowid DESC LIMIT ?", [*values, limit + 1]).fetchall()
        result = {"success": True, "project": principal.project_id, "events": [],
                  "supported_actions": list(QUALIFIED_ACTIONS), "next_before_id": None, "has_more": len(rows) > limit}
        for row in rows[:limit]:
            result["events"].append(project_row(row, principal.project_id))
            result["next_before_id"] = result["events"][-1]["id"] if result["has_more"] else None
            # Reserve the cursor before measuring: truncation can change null to
            # a UUID even when all SQL rows would otherwise fit on one page.
            bounded = {**result, "has_more": True, "next_before_id": result["events"][-1]["id"]}
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
    except (OSError, ValueError, TypeError, AttributeError, KeyError, RecursionError, sqlite3.Error) as exc:
        raise TaskAuditUnavailable("Qualified task audit unavailable") from exc
