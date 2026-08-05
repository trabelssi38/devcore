from pathlib import Path


SCHEMA_PATH = Path(__file__).resolve().parent / "postgres_schema_v1.sql"


def read_schema() -> str:
    return SCHEMA_PATH.read_text(encoding="utf-8").lower()


def test_postgres_schema_declares_core_tables() -> None:
    schema = read_schema()

    for table in [
        "organizations",
        "users",
        "workspaces",
        "workspace_memberships",
        "workspace_quotas",
        "projects",
        "tasks",
        "runs",
        "events",
        "plugins",
        "audit_log",
        "schedules",
        "schedule_history",
        "outbox_messages",
    ]:
        assert f"create table if not exists {table}" in schema


def test_postgres_schema_declares_identity_and_foreign_keys() -> None:
    schema = read_schema()

    assert "projects" in schema and "id text primary key" in schema
    assert "organization_id text not null references organizations(id)" in schema
    assert "workspace_id text not null references workspaces(id)" in schema
    assert "user_id text not null references users(id)" in schema
    assert "role text not null" in schema
    assert "role in ('owner', 'admin', 'developer', 'viewer')" in schema
    assert "runs_per_day integer not null" in schema
    assert "model_tokens_per_day integer not null" in schema
    assert "storage_mb integer not null" in schema
    assert "project_id text not null references projects(id)" in schema
    assert "task_id text references tasks(id)" in schema
    assert "run_id text references runs(id)" in schema
    assert "plugin_id text references plugins(id)" in schema
    assert "schedule_id text not null references schedules(id)" in schema
    assert "cron text not null" in schema
    assert "timezone text not null" in schema


def test_postgres_schema_declares_operational_indexes() -> None:
    schema = read_schema()

    for index in [
        "idx_tasks_project_status",
        "idx_workspaces_organization_status",
        "idx_workspace_memberships_workspace_role",
        "idx_workspace_quotas_workspace",
        "idx_runs_task_status",
        "idx_events_project_created",
        "idx_audit_log_project_created",
        "idx_schedules_project_status_next_run",
        "idx_schedule_history_schedule_occurred",
        "idx_outbox_messages_status_created",
    ]:
        assert f"create index if not exists {index}" in schema


def test_postgres_schema_preserves_json_extension_points() -> None:
    schema = read_schema()

    assert "metadata jsonb not null default '{}'::jsonb" in schema
    assert "payload jsonb not null default '{}'::jsonb" in schema
    assert "details jsonb not null default '{}'::jsonb" in schema
