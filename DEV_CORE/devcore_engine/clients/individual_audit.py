"""Bounded audit projection through HTTP; no server storage imports."""

from datetime import datetime
import json
import re
from urllib.parse import urlencode
from uuid import UUID

from devcore_engine.services.project_context import encode_context

MAX_AUDIT_RESPONSE_BYTES = 65536
ACTIONS = ("task.complete", "task.delete", "task.pause", "task.resume")
STATUSES = ("todo", "in_progress", "paused", "done", "blocked", "deleted")
TASK_AUDIT_TOOL = {
    "name": "devcore_task_audit",
    "description": "Consulte une page d'audit autorisée du projet via HTTP ; task.audit.read et responsable requis, auteur et versions seulement, pas d'historique global.",
    "input_schema": {"type": "object", "properties": {
        "project": {"type": "string"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        "task_id": {"type": "string", "maxLength": 128},
        "before_id": {"type": "string", "maxLength": 36},
    }, "required": ["project"], "additionalProperties": False},
}


def identifier(value):
    if (not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value)
            or ".." in value):
        raise ValueError("Invalid task identifier")
    return value


def audit_uuid(value):
    if not isinstance(value, str) or len(value) != 36 or str(UUID(value)) != value:
        raise ValueError("Invalid audit identifier")
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate audit JSON field")
        result[key] = value
    return result


def audit_page(raw, project, limit, task_id=None, before_id=None):
    value = json.loads(raw, object_pairs_hook=unique_object)
    if (not isinstance(value, dict) or value.get("success") is not True or value.get("project") != project
            or value.get("supported_actions") != list(ACTIONS) or not isinstance(value.get("events"), list)
            or len(value["events"]) > limit or type(value.get("has_more")) is not bool
            or "next_before_id" not in value):
        raise ValueError("Invalid scoped audit page")
    events, identifiers = [], set()
    for event in value["events"]:
        if not isinstance(event, dict) or event.get("project") != project or event.get("action") not in ACTIONS:
            raise ValueError("Invalid audit association")
        row_id, row_task = audit_uuid(event.get("id")), identifier(event.get("task_id"))
        if row_id in identifiers or row_id == before_id or (task_id is not None and row_task != task_id):
            raise ValueError("Invalid audit page association")
        identifiers.add(row_id)
        actor, created = event.get("actor"), event.get("created_at")
        if (not isinstance(actor, str) or not actor.strip() or len(actor) > 128
                or any(ord(c) < 32 or ord(c) == 127 for c in actor)
                or not isinstance(created, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", created)):
            raise ValueError("Invalid audit author or timestamp")
        datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
        states = {}
        for name in ("before", "after"):
            state = event.get(name)
            if (not isinstance(state, dict) or state.get("status") not in STATUSES
                    or type(state.get("version")) is not int or not 1 <= state["version"] <= 9223372036854775807):
                raise ValueError("Invalid audit state")
            states[name] = {"status": state["status"], "version": state["version"]}
        target = {"task.complete": "done", "task.delete": "deleted", "task.pause": "paused", "task.resume": "in_progress"}[event["action"]]
        source = {"task.pause": "in_progress", "task.resume": "paused"}.get(event["action"])
        if source is not None and states["before"]["status"] != source:
            raise ValueError("Invalid audit transition")
        if states["after"]["status"] != target or states["after"]["version"] != states["before"]["version"] + 1:
            raise ValueError("Invalid audit transition")
        events.append({"id": row_id, "project": project, "task_id": row_task, "actor": actor,
                       "action": event["action"], "created_at": created, **states})
    if value["has_more"]:
        if not events or audit_uuid(value["next_before_id"]) != events[-1]["id"]:
            raise ValueError("Invalid audit continuation")
    elif value["next_before_id"] is not None:
        raise ValueError("Unexpected audit continuation")
    result = {"success": True, "project": project, "events": events, "supported_actions": list(ACTIONS),
              "next_before_id": value["next_before_id"], "has_more": value["has_more"]}
    if len((encode_context(result) + "\n").encode("utf-8")) > MAX_AUDIT_RESPONSE_BYTES:
        raise ValueError("Audit projection exceeds bound")
    return result


def read_audit(client, arguments):
    try:
        if (not isinstance(arguments, dict) or set(arguments) - {"project", "limit", "task_id", "before_id"}
                or arguments.get("project") != client.project):
            raise ValueError("Explicit configured project required")
        limit = arguments.get("limit", 20)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Invalid audit limit")
        params = {"project": client.project, "limit": limit}
        if "task_id" in arguments:
            params["task_id"] = identifier(arguments["task_id"])
        if "before_id" in arguments:
            params["before_id"] = audit_uuid(arguments["before_id"])
    except (ValueError, TypeError, AttributeError):
        return {"success": False, "code": "invalid_arguments", "error": "Explicit configured project and valid audit arguments required"}
    return client._request("/api/project/task-audit?" + urlencode(params), max_bytes=MAX_AUDIT_RESPONSE_BYTES,
        family="audit", validator=lambda raw: audit_page(raw, client.project, limit,
            params.get("task_id"), params.get("before_id")))
