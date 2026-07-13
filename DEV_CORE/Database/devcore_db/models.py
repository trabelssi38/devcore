from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB


metadata = MetaData()


organizations = Table(
    "organizations",
    metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("status", String, nullable=False, server_default="active"),
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
    Column("status", String, nullable=False, server_default="active"),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


workspaces = Table(
    "workspaces",
    metadata,
    Column("id", Text, primary_key=True),
    Column("organization_id", Text, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    Column("name", Text, nullable=False),
    Column("status", String, nullable=False, server_default="active"),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("organization_id", "name", name="uq_workspaces_organization_name"),
)


projects = Table(
    "projects",
    metadata,
    Column("id", Text, primary_key=True),
    Column("workspace_id", Text, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    Column("name", Text, nullable=False),
    Column("root_path", Text, nullable=False),
    Column("status", String, nullable=False, server_default="active"),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


tasks = Table(
    "tasks",
    metadata,
    Column("id", Text, primary_key=True),
    Column("project_id", Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("title", Text, nullable=False),
    Column("mode", String, nullable=False, server_default="coding"),
    Column("status", String, nullable=False, server_default="todo"),
    Column("steps_done", Integer, nullable=False, server_default="0"),
    Column("steps_total", Integer, nullable=False, server_default="1"),
    Column("depends_on", Text, ForeignKey("tasks.id")),
    Column("worktree", Text),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("started_at", DateTime(timezone=True)),
    Column("completed_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("steps_done >= 0 and steps_total >= 1", name="tasks_steps_non_negative"),
    CheckConstraint("steps_done <= steps_total", name="tasks_steps_bounds"),
)


runs = Table(
    "runs",
    metadata,
    Column("id", Text, primary_key=True),
    Column("project_id", Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("task_id", Text, ForeignKey("tasks.id", ondelete="SET NULL")),
    Column("status", String, nullable=False, server_default="queued"),
    Column("runner", Text),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
    Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


plugins = Table(
    "plugins",
    metadata,
    Column("id", Text, primary_key=True),
    Column("project_id", Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("name", Text, nullable=False),
    Column("version", Text),
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
    Column("task_id", Text, ForeignKey("tasks.id", ondelete="SET NULL")),
    Column("run_id", Text, ForeignKey("runs.id", ondelete="SET NULL")),
    Column("plugin_id", Text, ForeignKey("plugins.id", ondelete="SET NULL")),
    Column("event_type", Text, nullable=False),
    Column("source", Text, nullable=False),
    Column("correlation_id", Text),
    Column("payload", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


audit_log = Table(
    "audit_log",
    metadata,
    Column("id", Text, primary_key=True),
    Column("project_id", Text, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("task_id", Text, ForeignKey("tasks.id", ondelete="SET NULL")),
    Column("run_id", Text, ForeignKey("runs.id", ondelete="SET NULL")),
    Column("plugin_id", Text, ForeignKey("plugins.id", ondelete="SET NULL")),
    Column("actor", Text, nullable=False, server_default="system"),
    Column("action", Text, nullable=False),
    Column("entity_type", Text, nullable=False),
    Column("entity_id", Text, nullable=False),
    Column("details", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


outbox_messages = Table(
    "outbox_messages",
    metadata,
    Column("id", Text, primary_key=True),
    Column("topic", Text, nullable=False),
    Column("payload", JSONB, nullable=False, server_default="{}"),
    Column("idempotency_key", Text, nullable=False, unique=True),
    Column("status", String, nullable=False, server_default="pending"),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("available_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("processed_at", DateTime(timezone=True)),
)


Index("idx_tasks_project_status", tasks.c.project_id, tasks.c.status, tasks.c.updated_at.desc())
Index("idx_workspaces_organization_status", workspaces.c.organization_id, workspaces.c.status, workspaces.c.updated_at.desc())
Index("idx_runs_task_status", runs.c.task_id, runs.c.status, runs.c.updated_at.desc())
Index("idx_events_project_created", events.c.project_id, events.c.created_at.desc())
Index("idx_audit_log_project_created", audit_log.c.project_id, audit_log.c.created_at.desc())
Index("idx_outbox_messages_status_created", outbox_messages.c.status, outbox_messages.c.created_at.asc())
