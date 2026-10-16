-- Add durable execution fields without making imported historical runs runnable.
-- Apply only after a full PostgreSQL backup and a verified maintenance preflight.
BEGIN;
SET LOCAL lock_timeout = '5s';

ALTER TABLE runs ADD COLUMN IF NOT EXISTS task_id text;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS title text;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS command jsonb;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS timeout_seconds double precision;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS attempt_number integer NOT NULL DEFAULT 0;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS max_attempts integer NOT NULL DEFAULT 3;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS worker_token text;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS heartbeat_at timestamptz;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS cancellation_requested boolean NOT NULL DEFAULT false;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS output text;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS error text;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS exit_code integer;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS idempotency_key text;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS actor text NOT NULL DEFAULT 'system';
ALTER TABLE runs ADD COLUMN IF NOT EXISTS env jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS execution_ready boolean NOT NULL DEFAULT false;
ALTER TABLE runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE runs FORCE ROW LEVEL SECURITY;

CREATE UNIQUE INDEX IF NOT EXISTS uq_runs_project_idempotency
    ON runs(project_id, idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_runs_ready_project_status_created
    ON runs(project_id, status, created_at) WHERE execution_ready;

CREATE TABLE IF NOT EXISTS external_effects (
    project_id text NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    idempotency_key text NOT NULL,
    effect_type text NOT NULL,
    status text NOT NULL,
    result jsonb,
    error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    PRIMARY KEY (project_id, idempotency_key, effect_type),
    CONSTRAINT external_effects_status CHECK (status IN ('pending', 'completed', 'failed'))
);
ALTER TABLE external_effects ENABLE ROW LEVEL SECURITY;
ALTER TABLE external_effects FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS rls_external_effects_project_isolation ON external_effects;
CREATE POLICY rls_external_effects_project_isolation ON external_effects
    FOR ALL USING (project_id = nullif(current_setting('app.current_project_id', true), ''))
    WITH CHECK (project_id = nullif(current_setting('app.current_project_id', true), ''));
DO $grant_app_roles$
DECLARE app_role text;
BEGIN
    FOREACH app_role IN ARRAY ARRAY['devcore_app', 'devcore_app_qualification'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = app_role) THEN
            EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON runs, external_effects TO %I', app_role);
        END IF;
    END LOOP;
END
$grant_app_roles$;

COMMIT;
