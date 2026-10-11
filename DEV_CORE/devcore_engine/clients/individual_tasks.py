"""Opt-in scoped tasks through the same API as the individual Cockpit."""

import json
import os
import re
from urllib.parse import urlencode

from .individual_context import CONTEXT_TOOL, IndividualContextClient
from .individual_audit import TASK_AUDIT_TOOL, read_audit


TASK_STATUS_TOOL = {
    "name": "devcore_task_status",
    "description": "Liste une page de tâches autorisées du projet via l'API ; versions observées, sans compteur global ni sélection implicite.",
    "input_schema": {"type": "object", "properties": {
        "project": {"type": "string"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        "offset": {"type": "integer", "minimum": 0},
    }, "required": ["project"], "additionalProperties": False},
}
TASK_DONE_TOOL = {
    "name": "devcore_task_done",
    "description": "Clôture une tâche explicitement nommée avec version attendue via l'API ; task.mutate requis, pas de retry, relire après résultat ou erreur de transport.",
    "input_schema": {"type": "object", "properties": {
        "project": {"type": "string"}, "task_id": {"type": "string"},
        "expected_version": {"type": "integer", "minimum": 1},
    }, "required": ["project", "task_id", "expected_version"], "additionalProperties": False},
}
MAX_TASK_RESPONSE_BYTES = 131072
TASK_DELETE_TOOL = {
    "name": "devcore_task_delete",
    "description": "Masque une tâche nommée avec version attendue via l'API ; activation de suppression et task.mutate requis, historique conservé, pas de retry.",
    "input_schema": {"type": "object", "properties": {
        "project": {"type": "string"}, "task_id": {"type": "string"},
        "expected_version": {"type": "integer", "minimum": 1},
    }, "required": ["project", "task_id", "expected_version"], "additionalProperties": False},
}


TASK_PAUSE_TOOL = {**TASK_DONE_TOOL, "name": "devcore_task_pause",
    "description": "Met en pause la tâche nommée avec version attendue ; activation explicite, task.mutate requis, pas de retry."}
TASK_RESUME_TOOL = {**TASK_DONE_TOOL, "name": "devcore_task_resume",
    "description": "Reprend la tâche nommée avec version attendue ; activation explicite, task.mutate requis, dépendances respectées, pas de retry."}


class IndividualApiClient(IndividualContextClient):
    def __init__(self, *args, task_access="disabled", delete_enabled=False, audit_enabled=False, transitions_enabled=False, **kwargs):
        if task_access not in {"disabled", "read", "write"}:
            raise ValueError("DEVCORE_MCP_TASK_ACCESS must be disabled, read or write")
        if type(delete_enabled) is not bool:
            raise ValueError("Explicit boolean delete_enabled required")
        if type(audit_enabled) is not bool:
            raise ValueError("Explicit boolean audit_enabled required")
        if type(transitions_enabled) is not bool:
            raise ValueError("Explicit boolean transitions_enabled required")
        super().__init__(*args, **kwargs)
        self.task_access = task_access
        self.delete_enabled = delete_enabled
        self.audit_enabled = audit_enabled
        self.transitions_enabled = transitions_enabled

    @classmethod
    def from_environment(cls):
        instance = super().from_environment()
        access = os.environ.get("DEVCORE_MCP_TASK_ACCESS", "disabled")
        if access not in {"disabled", "read", "write"}:
            raise ValueError("DEVCORE_MCP_TASK_ACCESS must be disabled, read or write")
        deletion = os.environ.get("DEVCORE_MCP_TASK_DELETE", "0")
        if deletion not in {"0", "1"}:
            raise ValueError("DEVCORE_MCP_TASK_DELETE must be 0 or 1")
        instance.task_access = "read" if access == "write" and os.environ.get("DEVCORE_MCP_READ_ONLY") == "1" else access
        instance.delete_enabled = deletion == "1"
        audit = os.environ.get("DEVCORE_MCP_TASK_AUDIT", "0")
        if audit not in {"0", "1"}:
            raise ValueError("DEVCORE_MCP_TASK_AUDIT must be 0 or 1")
        instance.audit_enabled = audit == "1"
        transitions = os.environ.get("DEVCORE_MCP_TASK_TRANSITIONS", "0")
        if transitions not in {"0", "1"}:
            raise ValueError("DEVCORE_MCP_TASK_TRANSITIONS must be 0 or 1")
        instance.transitions_enabled = transitions == "1"
        return instance

    @property
    def tools(self):
        tools = [CONTEXT_TOOL]
        if self.audit_enabled:
            tools.append(TASK_AUDIT_TOOL)
        if self.task_access in {"read", "write"}:
            tools.append(TASK_STATUS_TOOL)
        if self.task_access == "write":
            tools.append(TASK_DONE_TOOL)
            if self.transitions_enabled:
                tools.extend([TASK_PAUSE_TOOL, TASK_RESUME_TOOL])
            if self.delete_enabled:
                tools.append(TASK_DELETE_TOOL)
        return tools

    def _task_page(self, raw, project, limit, offset):
        rows = json.loads(raw)
        if not isinstance(rows, list) or len(rows) > limit:
            raise ValueError("Invalid task page")
        tasks, identifiers = [], set()
        for row in rows:
            if (not isinstance(row, dict) or row.get("project") != project
                    or not isinstance(row.get("id"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", row["id"])
                    or row["id"] in identifiers or not isinstance(row.get("title"), str)
                    or row.get("status") not in {"todo", "in_progress", "paused", "done", "blocked"}
                    or "version" not in row or (row["version"] is not None and
                        (type(row["version"]) is not int or not 1 <= row["version"] <= 9223372036854775807))):
                raise ValueError("Invalid scoped task row")
            identifiers.add(row["id"])
            tasks.append({key: row[key] for key in ("id", "project", "title", "status", "version")})
        return {"success": True, "project": project, "tasks": tasks, "limit": limit, "offset": offset,
                "page_may_have_more": len(rows) == limit}

    def _acknowledgement(self, raw, project, task_id, version):
        value = json.loads(raw)
        if not isinstance(value, dict) or value.get("status") != "success" or not isinstance(value.get("message"), str):
            raise ValueError("Invalid mutation acknowledgement")
        # This route doesn't return the committed row/version. Never infer it or issue a second write.
        return {"success": True, "project": project, "requested_task_id": task_id,
                "expected_version": version, "acknowledged": True, "refresh_required": True}

    def call(self, tool_name, arguments):
        if tool_name == CONTEXT_TOOL["name"]:
            return super().call(tool_name, arguments)
        if tool_name not in {tool["name"] for tool in self.tools}:
            return {"success": False, "code": "individual_tool_unavailable", "error": "Tool unavailable in the individual profile"}
        if tool_name == TASK_AUDIT_TOOL["name"]:
            return read_audit(self, arguments)
        mutation = tool_name in {TASK_DONE_TOOL["name"], TASK_DELETE_TOOL["name"], TASK_PAUSE_TOOL["name"], TASK_RESUME_TOOL["name"]}
        try:
            allowed = {"project", "task_id", "expected_version"} if mutation else {"project", "limit", "offset"}
            if not isinstance(arguments, dict) or set(arguments) - allowed or arguments.get("project") != self.project:
                raise ValueError("Explicit configured project and supported arguments required")
            project = self.project
            if mutation:
                task_id, version = arguments.get("task_id"), arguments.get("expected_version")
                if (not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", task_id)
                        or ".." in task_id or type(version) is not int or not 1 <= version <= 9223372036854775807):
                    raise ValueError("Named task and positive expected_version required")
            else:
                limit, offset = arguments.get("limit", 20), arguments.get("offset", 0)
                if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or not 0 <= offset <= 9223372036854775807:
                    raise ValueError("Valid pagination required")
        except (ValueError, TypeError):
            return {"success": False, "code": "invalid_arguments", "error": "Explicit configured project and valid task arguments required"}
        if mutation:
            body = json.dumps({"project": project, "id": task_id, "expected_version": version}).encode("utf-8")
            deletion = tool_name == TASK_DELETE_TOOL["name"]
            path = {TASK_DONE_TOOL["name"]: "/api/done", TASK_DELETE_TOOL["name"]: "/api/delete",
                    TASK_PAUSE_TOOL["name"]: "/api/pause", TASK_RESUME_TOOL["name"]: "/api/resume"}[tool_name]
            return self._request(path, method="DELETE" if deletion else "POST",
                body=body, max_bytes=4096, family="task", mutation=True,
                validator=lambda raw: self._acknowledgement(raw, project, task_id, version))
        return self._request("/api/dashboard/tasks?" + urlencode({"project": project, "limit": limit, "offset": offset}),
            max_bytes=MAX_TASK_RESPONSE_BYTES, family="task",
            validator=lambda raw: self._task_page(raw, project, limit, offset))
