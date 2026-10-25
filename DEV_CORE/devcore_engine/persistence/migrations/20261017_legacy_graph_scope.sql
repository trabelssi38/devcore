-- Scope the verified historical graph for project reads. The 14,625
-- cross-project edges remain in legacy_kg_edges with a quarantine reason.
-- Run only after audit_postgres_graph_scope.py matches every source row.
BEGIN;
SET LOCAL lock_timeout = '5s';

ALTER TABLE legacy_kg_nodes ADD COLUMN IF NOT EXISTS project_id text;
ALTER TABLE legacy_kg_edges ADD COLUMN IF NOT EXISTS project_id text;
ALTER TABLE legacy_kg_edges ADD COLUMN IF NOT EXISTS quarantine_reason text;

UPDATE legacy_kg_nodes
SET project_id = CASE
    WHEN id IN ('project:cea_dashboard', 'project:dashboard_recette_br',
                'project:job_tracker', 'project:scripts')
        THEN substring(id FROM 9)
    ELSE 'devcore'
END
WHERE project_id IS NULL;

UPDATE legacy_kg_edges AS edge
SET project_id = CASE
        WHEN src.project_id = 'devcore' AND dst.project_id = 'devcore'
            THEN 'devcore'
        ELSE NULL
    END,
    quarantine_reason = CASE
        WHEN src.project_id = 'devcore' AND dst.project_id = 'devcore'
            THEN NULL
        ELSE 'cross_project_endpoints'
    END
FROM legacy_kg_nodes AS src, legacy_kg_nodes AS dst
WHERE edge.from_node = src.id AND edge.to_node = dst.id
  AND edge.project_id IS NULL AND edge.quarantine_reason IS NULL;

ALTER TABLE legacy_kg_nodes ALTER COLUMN project_id SET NOT NULL;
DO $graph_constraints$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'legacy_kg_nodes_project_fk') THEN
        ALTER TABLE legacy_kg_nodes
            ADD CONSTRAINT legacy_kg_nodes_project_fk FOREIGN KEY (project_id)
            REFERENCES projects(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'legacy_kg_edges_scope_check') THEN
        ALTER TABLE legacy_kg_edges
            ADD CONSTRAINT legacy_kg_edges_scope_check CHECK (
                (project_id IS NOT NULL AND quarantine_reason IS NULL) OR
                (project_id IS NULL AND quarantine_reason = 'cross_project_endpoints'));
    END IF;
END
$graph_constraints$;

CREATE INDEX IF NOT EXISTS legacy_kg_nodes_project_idx
    ON legacy_kg_nodes(project_id);
CREATE INDEX IF NOT EXISTS legacy_kg_edges_project_idx
    ON legacy_kg_edges(project_id) WHERE quarantine_reason IS NULL;

ALTER TABLE legacy_kg_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE legacy_kg_nodes FORCE ROW LEVEL SECURITY;
ALTER TABLE legacy_kg_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE legacy_kg_edges FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS legacy_kg_nodes_project_read ON legacy_kg_nodes;
CREATE POLICY legacy_kg_nodes_project_read ON legacy_kg_nodes FOR SELECT
    USING (project_id = nullif(current_setting('app.current_project_id', true), ''));
DROP POLICY IF EXISTS legacy_kg_edges_project_read ON legacy_kg_edges;
CREATE POLICY legacy_kg_edges_project_read ON legacy_kg_edges FOR SELECT
    USING (project_id = nullif(current_setting('app.current_project_id', true), '')
           AND quarantine_reason IS NULL);

CREATE TABLE IF NOT EXISTS project_graph_stats (
    project_id text PRIMARY KEY REFERENCES projects(id),
    node_count bigint NOT NULL CHECK (node_count >= 0),
    edge_rows bigint NOT NULL CHECK (edge_rows >= 0),
    measured_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO project_graph_stats(project_id,node_count,edge_rows)
SELECT project_id, count(*),
       (SELECT count(*) FROM legacy_kg_edges e WHERE e.project_id=n.project_id
        AND e.quarantine_reason IS NULL)
FROM legacy_kg_nodes n GROUP BY project_id
ON CONFLICT (project_id) DO UPDATE SET
    node_count=EXCLUDED.node_count, edge_rows=EXCLUDED.edge_rows,
    measured_at=now();
ALTER TABLE project_graph_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_graph_stats FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS project_graph_stats_project_read ON project_graph_stats;
CREATE POLICY project_graph_stats_project_read ON project_graph_stats FOR SELECT
    USING (project_id = nullif(current_setting('app.current_project_id', true), ''));

DO $grant_graph_roles$
DECLARE app_role text;
BEGIN
    FOREACH app_role IN ARRAY ARRAY['devcore_app', 'devcore_app_qualification'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = app_role) THEN
            EXECUTE format('GRANT SELECT ON legacy_kg_nodes, legacy_kg_edges, project_graph_stats TO %I', app_role);
        END IF;
    END LOOP;
END
$grant_graph_roles$;
COMMIT;
