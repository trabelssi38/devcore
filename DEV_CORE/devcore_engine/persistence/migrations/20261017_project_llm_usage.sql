-- Durable project-attributed LLM usage. No historical/unattributed router
-- counters are imported into this table.
BEGIN;
SET LOCAL lock_timeout = '5s';

CREATE TABLE IF NOT EXISTS project_llm_usage (
    id text PRIMARY KEY,
    project_id text NOT NULL REFERENCES projects(id),
    user_id text NOT NULL,
    trace_id text NOT NULL,
    provider text NOT NULL,
    model text NOT NULL,
    prompt_tokens bigint CHECK (prompt_tokens >= 0),
    completion_tokens bigint CHECK (completion_tokens >= 0),
    usage_source text NOT NULL CHECK (usage_source IN ('provider_reported','unreported')),
    recorded_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (project_id, trace_id),
    CHECK ((usage_source='provider_reported' AND prompt_tokens IS NOT NULL
            AND completion_tokens IS NOT NULL) OR
           (usage_source='unreported' AND prompt_tokens IS NULL
            AND completion_tokens IS NULL))
);
CREATE INDEX IF NOT EXISTS project_llm_usage_recent_idx
    ON project_llm_usage(project_id, recorded_at DESC);
ALTER TABLE project_llm_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_llm_usage FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS project_llm_usage_select ON project_llm_usage;
CREATE POLICY project_llm_usage_select ON project_llm_usage FOR SELECT
    USING (project_id = nullif(current_setting('app.current_project_id', true), ''));
DROP POLICY IF EXISTS project_llm_usage_insert ON project_llm_usage;
CREATE POLICY project_llm_usage_insert ON project_llm_usage FOR INSERT
    WITH CHECK (project_id = nullif(current_setting('app.current_project_id', true), ''));

DO $grant_usage_roles$
DECLARE app_role text;
BEGIN
    FOREACH app_role IN ARRAY ARRAY['devcore_app', 'devcore_app_qualification'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = app_role) THEN
            EXECUTE format('GRANT SELECT, INSERT ON project_llm_usage TO %I', app_role);
        END IF;
    END LOOP;
END
$grant_usage_roles$;
COMMIT;
