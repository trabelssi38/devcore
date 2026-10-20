-- Phase 1: project-scoped evidence of automation hooks, separate from cron schedules.
-- Apply only through a qualified migration; this file does not activate hooks.
BEGIN;
SET LOCAL lock_timeout = '5s';
CREATE TABLE IF NOT EXISTS automation_hook_events (
    id text PRIMARY KEY,
    project_id text NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    actor text NOT NULL,
    hook text NOT NULL CHECK (hook IN ('session_start','session_end','git_commit','tool_use')),
    source text NOT NULL,
    correlation_id text,
    idempotency_key text NOT NULL,
    status text NOT NULL CHECK (status IN ('running','succeeded','failed')),
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    UNIQUE (project_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_automation_hook_events_project_created
    ON automation_hook_events(project_id, created_at DESC, id DESC);

ALTER TABLE automation_hook_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE automation_hook_events FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rls_automation_hook_events_project_isolation
    ON automation_hook_events;
CREATE POLICY rls_automation_hook_events_project_isolation
    ON automation_hook_events FOR ALL
    USING (project_id = nullif(current_setting('app.current_project_id', true), ''))
    WITH CHECK (project_id = nullif(current_setting('app.current_project_id', true), ''));

DO $grant_app_roles$
DECLARE app_role text;
BEGIN
    FOREACH app_role IN ARRAY ARRAY['devcore_app', 'devcore_app_qualification'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = app_role) THEN
            EXECUTE format('GRANT SELECT, INSERT, UPDATE ON automation_hook_events TO %I', app_role);
        END IF;
    END LOOP;
END
$grant_app_roles$;
COMMIT;
