-- DEV_CORE PostgreSQL Schema v2 (Team Profile & Multi-User Architecture)
-- Target source of truth for organizations, users, sessions, workspaces, projects,
-- project_memberships, tasks, runs, events, audit_log, outbox, artifacts, memory, budgets, schedules.

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
    password_hash text,
    status text not null default 'active',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists sessions (
    id text primary key,
    user_id text not null references users(id) on delete cascade,
    token_hash text not null unique,
    csrf_token_hash text,
    expires_at timestamptz not null,
    revoked_at timestamptz,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
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

create table if not exists workspace_quotas (
    workspace_id text primary key references workspaces(id) on delete cascade,
    runs_per_day integer not null,
    model_tokens_per_day integer not null,
    storage_mb integer not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint workspace_quotas_non_negative check (
        runs_per_day >= 0 and model_tokens_per_day >= 0 and storage_mb >= 0
    )
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

create table if not exists project_memberships (
    id text primary key,
    project_id text not null references projects(id) on delete cascade,
    user_id text not null references users(id) on delete cascade,
    role text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint project_memberships_role check (role in ('owner', 'maintainer', 'contributor', 'reader')),
    unique (project_id, user_id)
);

create table if not exists tasks (
    task_uuid uuid primary key,
    project_id text not null references projects(id) on delete cascade,
    task_number integer not null,
    legacy_id text,
    title text not null,
    mode text not null default 'coding',
    status text not null default 'todo',
    version integer not null default 1,
    steps_done integer not null default 0,
    steps_total integer not null default 1,
    depends_on_uuid uuid references tasks(task_uuid) on delete set null,
    worktree text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    started_at timestamptz,
    completed_at timestamptz,
    updated_at timestamptz not null default now(),
    constraint uq_tasks_project_task_number unique (project_id, task_number),
    constraint tasks_steps_non_negative check (steps_done >= 0 and steps_total >= 1),
    constraint tasks_steps_bounds check (steps_done <= steps_total),
    constraint tasks_version_positive check (version >= 1)
);

create table if not exists runs (
    id text primary key,
    project_id text not null references projects(id) on delete cascade,
    task_uuid uuid references tasks(task_uuid) on delete set null,
    status text not null default 'queued',
    runner text,
    task_id text,
    title text,
    command jsonb,
    timeout_seconds double precision,
    attempt_number integer not null default 0,
    max_attempts integer not null default 3,
    worker_token text,
    heartbeat_at timestamptz,
    cancellation_requested boolean not null default false,
    output text,
    error text,
    exit_code integer,
    idempotency_key text,
    actor text not null default 'system',
    env jsonb not null default '{}'::jsonb,
    execution_ready boolean not null default false,
    started_at timestamptz,
    finished_at timestamptz,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists uq_runs_project_idempotency
    on runs(project_id, idempotency_key) where idempotency_key is not null;
create index if not exists idx_runs_ready_project_status_created
    on runs(project_id, status, created_at) where execution_ready;

create table if not exists external_effects (
    project_id text not null references projects(id) on delete cascade,
    idempotency_key text not null,
    effect_type text not null,
    status text not null,
    result jsonb,
    error text,
    created_at timestamptz not null default now(),
    completed_at timestamptz,
    primary key (project_id, idempotency_key, effect_type),
    constraint external_effects_status check (status in ('pending', 'completed', 'failed'))
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
    task_uuid uuid references tasks(task_uuid) on delete set null,
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
    task_uuid uuid references tasks(task_uuid) on delete set null,
    run_id text references runs(id) on delete set null,
    plugin_id text references plugins(id) on delete set null,
    actor text not null default 'system',
    action text not null,
    entity_type text not null,
    entity_id text not null,
    details jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists schedules (
    id text primary key,
    project_id text not null references projects(id) on delete cascade,
    name text not null,
    cron text not null,
    timezone text not null,
    status text not null default 'active',
    next_run_at timestamptz,
    last_run_at timestamptz,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint schedules_status check (status in ('active', 'paused', 'disabled'))
);

create table if not exists schedule_history (
    id text primary key,
    schedule_id text not null references schedules(id) on delete cascade,
    run_id text references runs(id) on delete set null,
    event_type text not null,
    status text not null,
    details jsonb not null default '{}'::jsonb,
    occurred_at timestamptz not null default now()
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

create table if not exists artifacts (
    id text primary key,
    project_id text not null references projects(id) on delete cascade,
    task_uuid uuid references tasks(task_uuid) on delete set null,
    run_id text references runs(id) on delete set null,
    path text not null,
    digest text not null,
    size_bytes bigint not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique (project_id, path)
);

create table if not exists memory_entries (
    id text primary key,
    project_id text not null references projects(id) on delete cascade,
    name text not null,
    task_type text not null default 'general',
    content text not null,
    metadata jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now(),
    unique (project_id, name, task_type)
);

create table if not exists budgets (
    id text primary key,
    project_id text not null references projects(id) on delete cascade,
    model_tokens_daily integer not null default 0,
    runs_daily integer not null default 0,
    storage_mb integer not null default 0,
    metadata jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now(),
    unique (project_id)
);

-- Operational indexes
create index if not exists idx_tasks_project_status
    on tasks (project_id, status, updated_at desc);

create index if not exists idx_tasks_project_task_number
    on tasks (project_id, task_number);

create index if not exists idx_sessions_user_token
    on sessions (user_id, token_hash);

create index if not exists idx_project_memberships_project_role
    on project_memberships (project_id, role);

create index if not exists idx_runs_task_status
    on runs (task_uuid, status, updated_at desc);

create index if not exists idx_events_project_created
    on events (project_id, created_at desc);

create index if not exists idx_audit_log_project_created
    on audit_log (project_id, created_at desc);

create index if not exists idx_schedules_project_status_next_run
    on schedules (project_id, status, next_run_at asc);

create index if not exists idx_schedule_history_schedule_occurred
    on schedule_history (schedule_id, occurred_at desc);

create index if not exists idx_outbox_messages_status_created
    on outbox_messages (status, created_at asc);

create index if not exists idx_artifacts_project_digest
    on artifacts (project_id, digest);

create index if not exists idx_memory_project_name
    on memory_entries (project_id, name);

-- Row Level Security (RLS) setup for project isolation
alter table tasks enable row level security;
alter table runs enable row level security;
alter table runs force row level security;
alter table external_effects enable row level security;
alter table external_effects force row level security;
alter table events enable row level security;
alter table audit_log enable row level security;
alter table artifacts enable row level security;
alter table memory_entries enable row level security;
alter table budgets enable row level security;
alter table schedules enable row level security;
alter table schedules force row level security;
alter table schedule_history enable row level security;
alter table schedule_history force row level security;

create policy rls_tasks_project_isolation on tasks
    for all using (project_id = nullif(current_setting('app.current_project_id', true), ''));

create policy rls_runs_project_isolation on runs
    for all using (project_id = nullif(current_setting('app.current_project_id', true), ''));

create policy rls_external_effects_project_isolation on external_effects
    for all using (project_id = nullif(current_setting('app.current_project_id', true), ''))
    with check (project_id = nullif(current_setting('app.current_project_id', true), ''));

create policy rls_events_project_isolation on events
    for all using (project_id = nullif(current_setting('app.current_project_id', true), ''));

create policy rls_audit_log_project_isolation on audit_log
    for all using (project_id = nullif(current_setting('app.current_project_id', true), ''));

create policy rls_artifacts_project_isolation on artifacts
    for all using (project_id = nullif(current_setting('app.current_project_id', true), ''));

create policy rls_memory_project_isolation on memory_entries
    for all using (project_id = nullif(current_setting('app.current_project_id', true), ''));

create policy rls_budgets_project_isolation on budgets
    for all using (project_id = nullif(current_setting('app.current_project_id', true), ''));

create policy rls_schedules_project_isolation on schedules
    for all using (project_id = nullif(current_setting('app.current_project_id', true), ''))
    with check (project_id = nullif(current_setting('app.current_project_id', true), ''));

create policy rls_schedule_history_project_isolation on schedule_history
    for all using (exists (
        select 1 from schedules s where s.id = schedule_history.schedule_id
        and s.project_id = nullif(current_setting('app.current_project_id', true), '')
    )) with check (exists (
        select 1 from schedules s where s.id = schedule_history.schedule_id
        and s.project_id = nullif(current_setting('app.current_project_id', true), '')
    ));
