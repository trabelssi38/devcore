"""Individual API consultation, never through a client database."""

import json
from datetime import date
from http.client import HTTPException
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from devcore_engine.context import validate_project_id
from devcore_engine.security.secret_files import check_credential_file
from devcore_engine.services.project_context import encode_context


CONTEXT_TOOL = {
    "name": "devcore_project_context",
    "description": "Charge fiche et décisions via l'API avec autorisation individuelle context.read ; plafond en octets UTF-8, pas tokens.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project": {"type": "string"},
            "budget_bytes": {"type": "integer", "minimum": 256, "maximum": 65536},
            "query": {"type": "string", "maxLength": 4096},
        },
        "required": ["project"], "additionalProperties": False,
    },
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward a credential to a redirected endpoint, even on the same host.
        return None


class IndividualContextClient:
    def __init__(self, origin, credential_file, project, *, max_bytes=12000, timeout=10):
        parsed = urlsplit(origin)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
                or any(char.isspace() for char in origin)
                or (parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "::1", "localhost"})):
            raise ValueError("Explicit API origin required; HTTP is restricted to loopback")
        parsed.port  # Reject malformed ports before opening a credential.
        self.origin = origin.rstrip("/")
        self.credential_file = Path(credential_file)
        if not self.credential_file.is_absolute():
            raise ValueError("Absolute individual credential file required")
        self.project = validate_project_id(project)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", self.project):
            raise ValueError("Invalid configured project")
        if type(max_bytes) is not int or not 256 <= max_bytes <= 65536:
            raise ValueError("Invalid configured context limit")
        if type(timeout) is not int or not 1 <= timeout <= 30:
            raise ValueError("API socket timeout must be 1..30 seconds")
        self.max_bytes, self.timeout = max_bytes, timeout

    @classmethod
    def from_environment(cls):
        return cls(os.environ.get("DEVCORE_MCP_API_URL", ""),
                   os.environ.get("DEVCORE_MCP_CREDENTIAL_FILE", ""),
                   os.environ.get("DEVCORE_MCP_PROJECT", ""),
                   max_bytes=int(os.environ.get("DEVCORE_CONTEXT_MAX_BYTES", "12000")),
                   timeout=int(os.environ.get("DEVCORE_MCP_API_TIMEOUT_SECONDS", "10")))

    def _authorization(self):
        if os.name != "nt":
            raise PermissionError("Individual credential protection requires Windows NTFS")
        # Check the original path before resolve() could hide a junction alias.
        check_credential_file(self.credential_file)
        with self.credential_file.open("rb") as stream:
            raw = stream.read(4097)
        if len(raw) > 4096:
            raise ValueError("Credential file too large")
        value = json.loads(raw)
        token = value.get("token") if isinstance(value, dict) else None
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{32,512}", token):
            raise ValueError("Invalid individual credential file")
        return "Bearer " + token

    def _validate_response(self, raw, project, budget):
        text = raw.decode("utf-8")
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError("Invalid context response")
        measurement = value.get("measurement", {})
        if (value.get("project") != project or type(value.get("schema_version")) is not int or value["schema_version"] != 1
                or not isinstance(value.get("card"), str) or not isinstance(measurement, dict)
                or measurement.get("unit") != "utf8_bytes"
                or measurement.get("scope") != "complete_json_line"
                or measurement.get("model_tokens_measured") is not False
                or type(measurement.get("used")) is not int or measurement["used"] != len(raw)
                or type(measurement.get("budget")) is not int or measurement["budget"] != budget
                or len(raw) > budget or encode_context(value) + "\n" != text):
            raise ValueError("Invalid measured context response")
        decisions, excluded = value.get("decisions"), value.get("excluded_superseded")
        if not isinstance(decisions, list) or not isinstance(excluded, list):
            raise ValueError("Invalid context decisions")
        identifiers = set()
        for decision in decisions:
            if (not isinstance(decision, dict) or decision.get("status") not in {"effective", "proposed"}
                    or type(decision.get("required")) is not bool
                    or (decision["required"] and decision["status"] != "effective")
                    or decision.get("id") in excluded):
                raise ValueError("Invalid context decision status")
            identifier = decision.get("id")
            if not isinstance(identifier, str) or not identifier or identifier in identifiers:
                raise ValueError("Invalid context decision identifier")
            identifiers.add(identifier)
            if any(not isinstance(decision.get(field), str) or not decision[field].strip()
                   for field in ("decision", "rationale", "validation")):
                raise ValueError("Missing context decision explanation")
            sources = decision.get("sources")
            if not isinstance(sources, list) or not sources or any(not isinstance(s, str) or not s for s in sources):
                raise ValueError("Missing context decision sources")
            if decision.get("date") is not None:
                if not isinstance(decision["date"], str):
                    raise ValueError("Invalid context decision date")
                date.fromisoformat(decision["date"])
        if (not isinstance(value.get("provenance"), dict) or not isinstance(value.get("warnings"), list)
                or not isinstance(value.get("omitted"), list)):
            raise ValueError("Missing context diagnostics")
        provenance = value["provenance"]
        if (any(not isinstance(provenance.get(field), str) or not re.fullmatch(r"[0-9a-f]{64}", provenance[field])
                for field in ("manifest_sha256", "card_sha256"))
                or provenance.get("source_contents_verified") is not False
                or not isinstance(provenance.get("reviewed_at"), str)):
            raise ValueError("Invalid context provenance")
        date.fromisoformat(provenance["reviewed_at"])
        if (any(w not in {"card_changed_since_review", "context_review_expired", "review_date_in_future"}
                for w in value["warnings"])
                or any(not isinstance(e, str) or not e or e in identifiers for e in excluded)
                or any(not isinstance(o, dict) or not isinstance(o.get("id"), str) or not o["id"]
                       or o["id"] in identifiers or o.get("reason") not in {"budget", "not_relevant"}
                       for o in value["omitted"])):
            raise ValueError("Invalid context omissions or warnings")
        return value

    def call(self, tool_name, arguments):
        if tool_name != CONTEXT_TOOL["name"]:
            return {"success": False, "code": "individual_tool_unavailable", "error": "Tool unavailable in the individual profile"}
        try:
            if not isinstance(arguments, dict) or set(arguments) - {"project", "budget_bytes", "query"}:
                raise ValueError("Unsupported arguments")
            if not isinstance(arguments.get("project"), str):
                raise ValueError("String project required")
            project = validate_project_id(arguments.get("project"))
            if project != self.project:
                raise ValueError("Project does not match configured project")
            budget = arguments.get("budget_bytes", self.max_bytes)
            query = arguments.get("query", "")
            if (type(budget) is not int or not 256 <= budget <= self.max_bytes
                    or not isinstance(query, str) or len(query) > 4096):
                raise ValueError("Invalid budget or query")
        except (ValueError, TypeError):
            return {"success": False, "code": "invalid_arguments", "error": "Explicit configured project and valid context arguments required"}
        return self._request("/api/project/context?" + urlencode({
            "project": project, "budget_bytes": budget, "query": query,
        }), max_bytes=budget, validator=lambda raw: self._validate_response(raw, project, budget))

    def _request(self, path, *, max_bytes, validator, body=None, family="context", mutation=False, method=None):
        """Bound transport shared by the individually admitted API operations."""
        try:
            authorization = self._authorization()  # Re-read rotation and re-check ACL on every call.
        except (OSError, ValueError, TypeError, RecursionError):
            return {"success": False, "code": "individual_credential_unavailable", "error": "Protected individual credential unavailable"}
        headers = {"Authorization": authorization, "Accept": "application/json",
                   "Accept-Encoding": "identity", "Cache-Control": "no-store"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(self.origin + path, data=body, headers=headers, method=method or ("POST" if mutation else "GET"))
        try:
            # No cookies, inherited proxy settings, redirects, retries or local-context fallback.
            with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=self.timeout) as response:
                if (response.status != 200 or response.headers.get_content_type() != "application/json"
                        or response.headers.get("Content-Encoding", "identity") != "identity"):
                    raise ValueError("Unexpected context response")
                raw = response.read(max_bytes + 1)
                if len(raw) > max_bytes:
                    raise ValueError("API response exceeds bound")
                return validator(raw)
        except HTTPError as exc:
            status = exc.code
            conflict = None
            if family == "task" and status == 409:
                try:
                    detail = json.loads(exc.read(4097)).get("detail")
                    if isinstance(detail, dict) and detail.get("code") in {"stale_task_version", "task_version_unavailable"}:
                        conflict = detail["code"]
                except (OSError, ValueError, TypeError, AttributeError, RecursionError, HTTPException):
                    pass
            exc.close()  # Do not return or log the remote error body.
            if mutation and status not in {400, 401, 403, 404, 409, 413, 422}:
                return {"success": False, "code": "mutation_outcome_unknown", "http_status": status,
                        "error": "Mutation outcome unknown; refresh task state before any new action", "refresh_required": True}
            code = {401: "individual_credential_rejected", 403: "project_access_denied",
                    413: family + "_budget_exceeded", 422: family + "_request_rejected",
                    503: family + "_unavailable"}.get(status, family + "_api_unavailable")
            if family == "task":
                code = conflict or {400: "invalid_arguments", 404: "task_not_found", 409: "task_conflict"}.get(status, code)
            elif family == "audit" and status == 400:
                code = "invalid_arguments"
            return {"success": False, "code": code, "http_status": status,
                    "error": "Individual API request refused; no partial result returned"}
        except (OSError, URLError, HTTPException, ValueError, TypeError, RecursionError):
            if mutation:
                return {"success": False, "code": "mutation_outcome_unknown",
                        "error": "Mutation outcome unknown; refresh task state before any new action", "refresh_required": True}
            return {"success": False, "code": family + "_api_unavailable", "error": "Individual API unavailable or invalid; no local fallback"}
