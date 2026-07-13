from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable, Mapping

from sqlalchemy import Select, select

from .models import audit_log, projects


MAX_AUDIT_LIMIT = 500
DEFAULT_AUDIT_LIMIT = 100
AUDIT_EXPORT_COLUMNS = (
    "id",
    "project_id",
    "task_id",
    "run_id",
    "plugin_id",
    "actor",
    "action",
    "entity_type",
    "entity_id",
    "details",
    "created_at",
)
SENSITIVE_DETAIL_KEYS = ("secret", "token", "password", "api_key", "apikey", "key")


@dataclass(frozen=True)
class AuditLogQuery:
    workspace_id: str | None = None
    project_id: str | None = None
    task_id: str | None = None
    run_id: str | None = None
    plugin_id: str | None = None
    actor: str | None = None
    action: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    limit: int = DEFAULT_AUDIT_LIMIT
    offset: int = 0

    def __post_init__(self) -> None:
        if self.limit < 1 or self.limit > MAX_AUDIT_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_AUDIT_LIMIT}")
        if self.offset < 0:
            raise ValueError("offset must be greater than or equal to 0")


def build_audit_log_select(query: AuditLogQuery) -> Select:
    statement = select(audit_log)

    if query.workspace_id:
        statement = statement.join(projects, audit_log.c.project_id == projects.c.id).where(
            projects.c.workspace_id == query.workspace_id
        )

    filters = {
        "project_id": query.project_id,
        "task_id": query.task_id,
        "run_id": query.run_id,
        "plugin_id": query.plugin_id,
        "actor": query.actor,
        "action": query.action,
        "entity_type": query.entity_type,
        "entity_id": query.entity_id,
    }
    for column_name, value in filters.items():
        if value:
            statement = statement.where(audit_log.c[column_name] == value)

    if query.created_from:
        statement = statement.where(audit_log.c.created_at >= query.created_from)
    if query.created_to:
        statement = statement.where(audit_log.c.created_at <= query.created_to)

    return statement.order_by(audit_log.c.created_at.desc()).limit(query.limit).offset(query.offset)


def redact_sensitive_details(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if any(marker in key_text.lower() for marker in SENSITIVE_DETAIL_KEYS):
                redacted[key_text] = "[REDACTED]"
            else:
                redacted[key_text] = redact_sensitive_details(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive_details(item) for item in value]
    return value


def normalize_audit_row(row: Mapping[str, Any]) -> dict[str, Any]:
    normalized = {column: row.get(column) for column in AUDIT_EXPORT_COLUMNS}
    normalized["details"] = redact_sensitive_details(normalized.get("details") or {})
    created_at = normalized.get("created_at")
    if isinstance(created_at, datetime):
        normalized["created_at"] = created_at.isoformat()
    elif isinstance(created_at, date):
        normalized["created_at"] = created_at.isoformat()
    return normalized


def export_audit_log_jsonl(rows: Iterable[Mapping[str, Any]]) -> str:
    lines = [
        json.dumps(normalize_audit_row(row), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in rows
    ]
    return "\n".join(lines) + ("\n" if lines else "")


def export_audit_log_csv(rows: Iterable[Mapping[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=AUDIT_EXPORT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        normalized = normalize_audit_row(row)
        normalized["details"] = json.dumps(normalized["details"], ensure_ascii=False, sort_keys=True)
        writer.writerow(normalized)
    return buffer.getvalue()
