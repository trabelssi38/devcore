-- DEV_CORE PostgreSQL schema v1
-- Source of truth target for organizations, users, workspaces, projects, tasks, runs, events, plugins, and audit.

create table if not exists organizations (
    id text primary key,
    name text not null,
    status text not null default 'active',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists users (
    id text primary key,
    email text not null unique,
    display_name text not null,
    status text not null default 'active',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists workspaces (
    id text primary key,
    organization_id text not null references organizations(id) on delete cascade,
    name text not null,
    status text not null default 'active',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (organization_id, name)
);

create table if not exists workspace_memberships (
    id text primary key,
    workspace_id text not null references workspaces(id) on delete cascade,
    user_id text not null references users(id) on delete cascade,
    role text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint workspace_memberships_role check (role in ('owner', 'admin', 'developer', 'viewer')),
    unique (workspace_id, user_id)
);

create table if not exists projects (
    id text primary key,
    workspace_id text not null references workspaces(id) on delete cascade,
    name text not null,
    root_path text not null,
    status text not null default 'active',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists tasks (
    id text primary key,
    project_id text not null references projects(id) on delete cascade,
    title text not null,
    mode text not null default 'coding',
    status text not null default 'todo',
    steps_done integer not null default 0,
    steps_total integer not null default 1,
    depends_on text references tasks(id),
    worktree text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    started_at timestamptz,
    completed_at timestamptz,
    updated_at timestamptz not null default now(),
    constraint tasks_steps_non_negative check (steps_done >= 0 and steps_total >= 1),
    constraint tasks_steps_bounds check (steps_done <= steps_total)
);

create table if not exists runs (
    id text primary key,
    project_id text not null references projects(id) on delete cascade,
    task_id text references tasks(id) on delete set null,
    status text not null default 'queued',
    runner text,
    started_at timestamptz,
    finished_at timestamptz,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists plugins (
    id text primary key,
    project_id text not null references projects(id) on delete cascade,
    name text not null,
    version text,
    enabled boolean not null default true,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (project_id, name)
);

create table if not exists events (
    id text primary key,
    project_id text not null references projects(id) on delete cascade,
    task_id text references tasks(id) on delete set null,
    run_id text references runs(id) on delete set null,
    plugin_id text references plugins(id) on delete set null,
    event_type text not null,
    source text not null,
    correlation_id text,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists audit_log (
    id text primary key,
    project_id text not null references projects(id) on delete cascade,
    task_id text references tasks(id) on delete set null,
    run_id text references runs(id) on delete set null,
    plugin_id text references plugins(id) on delete set null,
    actor text not null default 'system',
    action text not null,
    entity_type text not null,
    entity_id text not null,
    details jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists outbox_messages (
    id text primary key,
    topic text not null,
    payload jsonb not null default '{}'::jsonb,
    idempotency_key text not null unique,
    status text not null default 'pending',
    attempts integer not null default 0,
    created_at timestamptz not null default now(),
    available_at timestamptz not null default now(),
    processed_at timestamptz
);

create index if not exists idx_tasks_project_status
    on tasks (project_id, status, updated_at desc);

create index if not exists idx_workspaces_organization_status
    on workspaces (organization_id, status, updated_at desc);

create index if not exists idx_workspace_memberships_workspace_role
    on workspace_memberships (workspace_id, role);

create index if not exists idx_runs_task_status
    on runs (task_id, status, updated_at desc);

create index if not exists idx_events_project_created
    on events (project_id, created_at desc);

create index if not exists idx_audit_log_project_created
    on audit_log (project_id, created_at desc);

create index if not exists idx_outbox_messages_status_created
    on outbox_messages (status, created_at asc);
