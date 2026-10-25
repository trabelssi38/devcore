"""SQLAlchemy schema models for DEV_CORE target PostgreSQL architecture.

Exposes declarative Table objects with PostgreSQL dialects, JSONB support,
and UUID / JSON fallbacks for cross-dialect compatibility during tests.
"""

from __future__ import annotations

import uuid
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData()


organizations = Table(
    "organizations",
    metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("status", String(50), nullable=False, server_default="active"),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


users = Table(
    "users",
    metadata,
    Column("id", Text, primary_key=True),
    Column("email", Text, nullable=False, unique=True),
    Column("display_name", Text, nullable=False),
    Column("password_hash", Text, nullable=True),
    Column("status", String(50), nullable=False, server_default="active"),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


sessions = Table(
    "sessions",
    metadata,
    Column("id", Text, primary_key=True),
    Column("user_id", Text, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("token_hash", Text, nullable=False, unique=True),
    Column("csrf_token_hash", Text, nullable=True),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("revoked_at", DateTime(timezone=True), nullable=True),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


workspaces = Table(
    "workspaces",
    metadata,
    Column("id", Text, primary_key=True),
    Column("organization_id", Text, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    Column("name", Text, nullable=False),
    Column("status", String(50), nullable=False, server_default="active"),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("organization_id", "name", name="uq_workspaces_organization_name"),
)


workspace_memberships = Table(
    "workspace_memberships",
    metadata,
    Column("id", Text, primary_key=True),
    Column("workspace_id", Text, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", Text, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("role", String(50), nullable=False),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("role in ('owner', 'admin', 'developer', 'viewer')", name="workspace_memberships_role"),
    UniqueConstraint("workspace_id", "user_id", name="uq_workspace_memberships_workspace_user"),
)


workspace_quotas = Table(
    "workspace_quotas",
    metadata,
    Column("workspace_id", Text, ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True),
    Column("runs_per_day", Integer, nullable=False),
    Column("model_tokens_per_day", Integer, nullable=False),
    Column("storage_mb", Integer, nullable=False),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        "runs_per_day >= 0 and model_tokens_per_day >= 0 and storage_mb >= 0",
        name="workspace_quotas_non_negative",
    ),
)


projects = Table(
    "projects",
    metadata,
    Column("id", Text, primary_key=True),
    Column("workspace_id", Text, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    Column("name", Text, nullable=False),
    Column("root_path", Text, nullable=False),
    Column("status", String(50), nullable=False, server_default="active"),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


project_memberships = Table(
    "project_memberships",
    metadata,
    Column("id", Text, primary_key=True),
    Column("project_id", Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", Text, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("role", String(50), nullable=False),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("role in ('owner', 'maintainer', 'contributor', 'reader')", name="project_memberships_role"),
    UniqueConstraint("project_id", "user_id", name="uq_project_memberships_project_user"),
)


tasks = Table(
    "tasks",
    metadata,
    Column("task_uuid", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("project_id", Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("task_number", Integer, nullable=False),
    Column("legacy_id", Text, nullable=True),
    Column("title", Text, nullable=False),
    Column("mode", String(50), nullable=False, server_default="coding"),
    Column("status", String(50), nullable=False, server_default="todo"),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("steps_done", Integer, nullable=False, server_default="0"),
    Column("steps_total", Integer, nullable=False, server_default="1"),
    Column("depends_on_uuid", UUID(as_uuid=True), ForeignKey("tasks.task_uuid", ondelete="SET NULL"), nullable=True),
    Column("worktree", Text, nullable=True),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("project_id", "task_number", name="uq_tasks_project_task_number"),
    CheckConstraint("steps_done >= 0 and steps_total >= 1", name="tasks_steps_non_negative"),
    CheckConstraint("steps_done <= steps_total", name="tasks_steps_bounds"),
    CheckConstraint("version >= 1", name="tasks_version_positive"),
)


runs = Table(
    "runs",
    metadata,
    Column("id", Text, primary_key=True),
    Column("project_id", Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("task_uuid", UUID(as_uuid=True), ForeignKey("tasks.task_uuid", ondelete="SET NULL"), nullable=True),
    Column("status", String(50), nullable=False, server_default="queued"),
    Column("runner", Text, nullable=True),
    Column("task_id", Text, nullable=True),
    Column("title", Text, nullable=True),
    Column("command", JSONB, nullable=True),
    Column("timeout_seconds", Float, nullable=True),
    Column("attempt_number", Integer, nullable=False, server_default="0"),
    Column("max_attempts", Integer, nullable=False, server_default="3"),
    Column("worker_token", Text, nullable=True),
    Column("heartbeat_at", DateTime(timezone=True), nullable=True),
    Column("cancellation_requested", Boolean, nullable=False, server_default="false"),
    Column("output", Text, nullable=True),
    Column("error", Text, nullable=True),
    Column("exit_code", Integer, nullable=True),
    Column("idempotency_key", Text, nullable=True),
    Column("actor", Text, nullable=False, server_default="system"),
    Column("env", JSONB, nullable=False, server_default="{}"),
    Column("execution_ready", Boolean, nullable=False, server_default="false"),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


external_effects = Table(
    "external_effects",
    metadata,
    Column("project_id", Text, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("idempotency_key", Text, primary_key=True),
    Column("effect_type", Text, primary_key=True),
    Column("status", Text, nullable=False),
    Column("result", JSONB, nullable=True),
    Column("error", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    CheckConstraint("status in ('pending', 'completed', 'failed')", name="external_effects_status"),
)


plugins = Table(
    "plugins",
    metadata,
    Column("id", Text, primary_key=True),
    Column("project_id", Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("name", Text, nullable=False),
    Column("version", Text, nullable=True),
    Column("enabled", Boolean, nullable=False, server_default="true"),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("project_id", "name", name="uq_plugins_project_name"),
)


events = Table(
    "events",
    metadata,
    Column("id", Text, primary_key=True),
    Column("project_id", Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("task_uuid", UUID(as_uuid=True), ForeignKey("tasks.task_uuid", ondelete="SET NULL"), nullable=True),
    Column("run_id", Text, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True),
    Column("plugin_id", Text, ForeignKey("plugins.id", ondelete="SET NULL"), nullable=True),
    Column("event_type", Text, nullable=False),
    Column("source", Text, nullable=False),
    Column("correlation_id", Text, nullable=True),
    Column("payload", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


audit_log = Table(
    "audit_log",
    metadata,
    Column("id", Text, primary_key=True),
    Column("project_id", Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("task_uuid", UUID(as_uuid=True), ForeignKey("tasks.task_uuid", ondelete="SET NULL"), nullable=True),
    Column("run_id", Text, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True),
    Column("plugin_id", Text, ForeignKey("plugins.id", ondelete="SET NULL"), nullable=True),
    Column("actor", Text, nullable=False, server_default="system"),
    Column("action", Text, nullable=False),
    Column("entity_type", Text, nullable=False),
    Column("entity_id", Text, nullable=False),
    Column("details", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


schedules = Table(
    "schedules",
    metadata,
    Column("id", Text, primary_key=True),
    Column("project_id", Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("name", Text, nullable=False),
    Column("cron", Text, nullable=False),
    Column("timezone", Text, nullable=False),
    Column("status", String(50), nullable=False, server_default="active"),
    Column("next_run_at", DateTime(timezone=True), nullable=True),
    Column("last_run_at", DateTime(timezone=True), nullable=True),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("status in ('active', 'paused', 'disabled')", name="schedules_status"),
)


schedule_history = Table(
    "schedule_history",
    metadata,
    Column("id", Text, primary_key=True),
    Column("schedule_id", Text, ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False),
    Column("run_id", Text, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True),
    Column("event_type", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("details", JSONB, nullable=False, server_default="{}"),
    Column("occurred_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


outbox_messages = Table(
    "outbox_messages",
    metadata,
    Column("id", Text, primary_key=True),
    Column("topic", Text, nullable=False),
    Column("payload", JSONB, nullable=False, server_default="{}"),
    Column("idempotency_key", Text, nullable=False, unique=True),
    Column("status", String(50), nullable=False, server_default="pending"),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("available_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("processed_at", DateTime(timezone=True), nullable=True),
)


artifacts = Table(
    "artifacts",
    metadata,
    Column("id", Text, primary_key=True),
    Column("project_id", Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("task_uuid", UUID(as_uuid=True), ForeignKey("tasks.task_uuid", ondelete="SET NULL"), nullable=True),
    Column("run_id", Text, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True),
    Column("path", Text, nullable=False),
    Column("digest", Text, nullable=False),
    Column("size_bytes", BigInteger, nullable=False),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("project_id", "path", name="uq_artifacts_project_path"),
)


memory_entries = Table(
    "memory_entries",
    metadata,
    Column("id", Text, primary_key=True),
    Column("project_id", Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("name", Text, nullable=False),
    Column("task_type", Text, nullable=False, server_default="general"),
    Column("content", Text, nullable=False),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("project_id", "name", "task_type", name="uq_memory_project_name_type"),
)


budgets = Table(
    "budgets",
    metadata,
    Column("id", Text, primary_key=True),
    Column("project_id", Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True),
    Column("model_tokens_daily", Integer, nullable=False, server_default="0"),
    Column("runs_daily", Integer, nullable=False, server_default="0"),
    Column("storage_mb", Integer, nullable=False, server_default="0"),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


# Indexes
Index("idx_tasks_project_status", tasks.c.project_id, tasks.c.status, tasks.c.updated_at.desc())
Index("idx_tasks_project_task_number", tasks.c.project_id, tasks.c.task_number)
Index("idx_sessions_user_token", sessions.c.user_id, sessions.c.token_hash)
Index("idx_project_memberships_project_role", project_memberships.c.project_id, project_memberships.c.role)
Index("idx_workspaces_organization_status", workspaces.c.organization_id, workspaces.c.status, workspaces.c.updated_at.desc())
Index("idx_runs_task_status", runs.c.task_uuid, runs.c.status, runs.c.updated_at.desc())
Index("uq_runs_project_idempotency", runs.c.project_id, runs.c.idempotency_key,
      unique=True, postgresql_where=runs.c.idempotency_key.isnot(None))
Index("idx_runs_ready_project_status_created", runs.c.project_id, runs.c.status, runs.c.created_at,
      postgresql_where=runs.c.execution_ready)
Index("idx_events_project_created", events.c.project_id, events.c.created_at.desc())
Index("idx_audit_log_project_created", audit_log.c.project_id, audit_log.c.created_at.desc())
Index("idx_schedules_project_status_next_run", schedules.c.project_id, schedules.c.status, schedules.c.next_run_at.asc())
Index("idx_schedule_history_schedule_occurred", schedule_history.c.schedule_id, schedule_history.c.occurred_at.desc())
Index("idx_outbox_messages_status_created", outbox_messages.c.status, outbox_messages.c.created_at.asc())
Index("idx_artifacts_project_digest", artifacts.c.project_id, artifacts.c.digest)
Index("idx_memory_project_name", memory_entries.c.project_id, memory_entries.c.name)
