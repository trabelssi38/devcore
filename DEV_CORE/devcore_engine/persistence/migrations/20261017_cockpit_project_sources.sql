-- Read-only team Cockpit sources. Apply after a full verified database backup.
BEGIN;
SET LOCAL lock_timeout = '5s';

ALTER TABLE plugins ENABLE ROW LEVEL SECURITY;
ALTER TABLE plugins FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS rls_plugins_project_isolation ON plugins;
CREATE POLICY rls_plugins_project_isolation ON plugins
    FOR ALL USING (project_id = nullif(current_setting('app.current_project_id', true), ''))
    WITH CHECK (project_id = nullif(current_setting('app.current_project_id', true), ''));

ALTER TABLE memory_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_entries FORCE ROW LEVEL SECURITY;
ALTER TABLE budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets FORCE ROW LEVEL SECURITY;

DO $grant_cockpit_roles$
DECLARE app_role text;
BEGIN
    FOREACH app_role IN ARRAY ARRAY['devcore_app', 'devcore_app_qualification'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = app_role) THEN
            EXECUTE format('GRANT SELECT ON plugins, memory_entries, budgets TO %I', app_role);
        END IF;
    END LOOP;
END
$grant_cockpit_roles$;
COMMIT;
