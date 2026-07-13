import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.dialects import postgresql


DATABASE_ROOT = Path(__file__).resolve().parent
if str(DATABASE_ROOT) not in sys.path:
    sys.path.insert(0, str(DATABASE_ROOT))


def compile_sql(statement) -> str:
    return str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


def test_audit_log_query_filters_by_workspace_project_actor_action_and_date() -> None:
    from devcore_db.audit_log import AuditLogQuery, build_audit_log_select

    query = AuditLogQuery(
        workspace_id="wks_default",
        project_id="devcore",
        actor="usr_system",
        action="task.completed",
        created_from=datetime(2026, 7, 13, 8, 0, tzinfo=timezone.utc),
        created_to=datetime(2026, 7, 13, 18, 0, tzinfo=timezone.utc),
        limit=25,
    )

    sql = compile_sql(build_audit_log_select(query))

    assert "JOIN projects" in sql
    assert "projects.workspace_id = 'wks_default'" in sql
    assert "audit_log.project_id = 'devcore'" in sql
    assert "audit_log.actor = 'usr_system'" in sql
    assert "audit_log.action = 'task.completed'" in sql
    assert "audit_log.created_at >=" in sql
    assert "audit_log.created_at <=" in sql
    assert "ORDER BY audit_log.created_at DESC" in sql
    assert "LIMIT 25" in sql


def test_audit_log_query_rejects_unbounded_or_invalid_limits() -> None:
    from devcore_db.audit_log import AuditLogQuery

    for value in (0, 501):
        try:
            AuditLogQuery(limit=value)
        except ValueError as exc:
            assert "limit" in str(exc)
        else:
            raise AssertionError("invalid audit limit should be rejected")


def test_audit_log_jsonl_export_is_stable_and_redacts_secrets() -> None:
    from devcore_db.audit_log import export_audit_log_jsonl

    rows = [
        {
            "id": "aud_1",
            "project_id": "devcore",
            "actor": "usr_system",
            "action": "settings.updated",
            "entity_type": "settings",
            "entity_id": "runtime",
            "details": {"api_key": "secret-value", "safe": "visible"},
            "created_at": datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
        }
    ]

    exported = export_audit_log_jsonl(rows)
    parsed = json.loads(exported.strip())

    assert parsed["id"] == "aud_1"
    assert parsed["created_at"] == "2026-07-13T12:00:00+00:00"
    assert parsed["details"]["api_key"] == "[REDACTED]"
    assert parsed["details"]["safe"] == "visible"


def test_audit_log_csv_export_uses_fixed_columns_and_json_details() -> None:
    from devcore_db.audit_log import export_audit_log_csv

    rows = [
        {
            "id": "aud_1",
            "project_id": "devcore",
            "task_id": "T-201",
            "run_id": None,
            "plugin_id": None,
            "actor": "usr_system",
            "action": "audit.exported",
            "entity_type": "audit_log",
            "entity_id": "aud_1",
            "details": {"count": 1},
            "created_at": datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
        }
    ]

    exported = export_audit_log_csv(rows)
    parsed = list(csv.DictReader(exported.splitlines()))

    assert parsed[0]["id"] == "aud_1"
    assert parsed[0]["task_id"] == "T-201"
    assert json.loads(parsed[0]["details"]) == {"count": 1}
