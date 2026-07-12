from pathlib import Path


SCHEMA_PATH = Path(__file__).resolve().parent / "postgres_schema_v1.sql"


def read_schema() -> str:
    return SCHEMA_PATH.read_text(encoding="utf-8").lower()


def test_postgres_schema_declares_core_tables() -> None:
    schema = read_schema()

    for table in ["projects", "tasks", "runs", "events", "plugins", "audit_log", "outbox_messages"]:
        assert f"create table if not exists {table}" in schema


def test_postgres_schema_declares_identity_and_foreign_keys() -> None:
    schema = read_schema()

    assert "projects" in schema and "id text primary key" in schema
    assert "project_id text not null references projects(id)" in schema
    assert "task_id text references tasks(id)" in schema
    assert "run_id text references runs(id)" in schema
    assert "plugin_id text references plugins(id)" in schema


def test_postgres_schema_declares_operational_indexes() -> None:
    schema = read_schema()

    for index in [
        "idx_tasks_project_status",
        "idx_runs_task_status",
        "idx_events_project_created",
        "idx_audit_log_project_created",
        "idx_outbox_messages_status_created",
    ]:
        assert f"create index if not exists {index}" in schema


def test_postgres_schema_preserves_json_extension_points() -> None:
    schema = read_schema()

    assert "metadata jsonb not null default '{}'::jsonb" in schema
    assert "payload jsonb not null default '{}'::jsonb" in schema
    assert "details jsonb not null default '{}'::jsonb" in schema
