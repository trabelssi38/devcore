-- Scope existing schedules and their history to the current PostgreSQL project.
-- Apply only after a full backup and a verified maintenance preflight.
BEGIN;
SET LOCAL lock_timeout = '5s';

ALTER TABLE schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedules FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS rls_schedules_project_isolation ON schedules;
CREATE POLICY rls_schedules_project_isolation ON schedules
    FOR ALL USING (project_id = nullif(current_setting('app.current_project_id', true), ''))
    WITH CHECK (project_id = nullif(current_setting('app.current_project_id', true), ''));

ALTER TABLE schedule_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedule_history FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS rls_schedule_history_project_isolation ON schedule_history;
CREATE POLICY rls_schedule_history_project_isolation ON schedule_history
    FOR ALL USING (EXISTS (
        SELECT 1 FROM schedules s WHERE s.id = schedule_history.schedule_id
        AND s.project_id = nullif(current_setting('app.current_project_id', true), '')
    )) WITH CHECK (EXISTS (
        SELECT 1 FROM schedules s WHERE s.id = schedule_history.schedule_id
        AND s.project_id = nullif(current_setting('app.current_project_id', true), '')
    ));

GRANT SELECT, INSERT, UPDATE, DELETE ON schedules, schedule_history TO devcore_app;
COMMIT;
