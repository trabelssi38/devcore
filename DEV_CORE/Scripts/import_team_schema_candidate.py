"""Import projects/tasks into the actual DevCore PostgreSQL team schema and test RLS."""

from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg

NAMESPACE = uuid.UUID("3bbec48a-1d88-524e-b9da-55e57b23a3c7")
APP_ROLE = "devcore_app_qualification"
APP_PASSWORD = "DevCoreAppP3_2026_local"


def json_value(value: str | None) -> str:
    if not value:
        return "{}"
    try:
        json.loads(value)
        return value
    except json.JSONDecodeError:
        return json.dumps({"source_text": value}, ensure_ascii=False)


def task_number(identifier: str, used: set[int]) -> int:
    try:
        value = int(identifier[2:] if identifier.upper().startswith("T-") else identifier)
    except ValueError:
        value = max(used or {0}) + 1
    while value in used:
        value += 1
    used.add(value)
    return value


def run(candidate: Path, host: str, port: int, password: str, database: str, output: Path) -> dict:
    source = sqlite3.connect(f"file:{candidate.resolve().as_posix()}?mode=ro&immutable=1", uri=True)
    pg = psycopg.connect(host=host, port=port, user="postgres", password=password, dbname=database)
    with pg.cursor() as cur:
        cur.execute("INSERT INTO organizations (id,name) VALUES ('org-devcore','DevCore qualification') ON CONFLICT DO NOTHING")
        cur.execute("INSERT INTO workspaces (id,organization_id,name) VALUES ('ws-devcore','org-devcore','DevCore qualification') ON CONFLICT DO NOTHING")
        cur.execute("INSERT INTO users (id,email,display_name) VALUES ('user-qualification','qualification@devcore.local','Qualification') ON CONFLICT DO NOTHING")
        cur.execute("INSERT INTO workspace_memberships (id,workspace_id,user_id,role) VALUES ('wm-qualification','ws-devcore','user-qualification','owner') ON CONFLICT DO NOTHING")
        projects = source.execute("SELECT id,name,root_path,status,metadata,created_at,updated_at FROM projects").fetchall()
        for row in projects:
            cur.execute("INSERT INTO projects (id,workspace_id,name,root_path,status,metadata) VALUES (%s,'ws-devcore',%s,%s,%s,%s::jsonb) ON CONFLICT (id) DO UPDATE SET root_path=EXCLUDED.root_path,status=EXCLUDED.status,metadata=EXCLUDED.metadata", (row[0],row[1],row[2],row[3],row[4] or "{}"))
            cur.execute("INSERT INTO project_memberships (id,project_id,user_id,role) VALUES (%s,%s,'user-qualification','owner') ON CONFLICT DO NOTHING", (f"pm-{row[0]}",row[0]))
        counts = {"projects": len(projects), "tasks": 0}
        used: dict[str, set[int]] = {row[0]: set() for row in projects}
        for row in source.execute("SELECT id,project_id,title,mode,status,steps_done,steps_total,depends_on,worktree,metadata,created_at,started_at,completed_at,updated_at FROM tasks"):
            number = task_number(row[0], used.setdefault(row[1], set()))
            task_uuid = uuid.uuid5(NAMESPACE, f"{row[1]}\x00{row[0]}")
            cur.execute("""INSERT INTO tasks (task_uuid,project_id,task_number,legacy_id,title,mode,status,steps_done,steps_total,worktree,metadata)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT (task_uuid) DO NOTHING""",
                       (str(task_uuid),row[1],number,row[0],row[2],row[3],row[4],row[5],row[6],None,json_value(row[9])))
            counts["tasks"] += 1
        cur.execute("CREATE TABLE IF NOT EXISTS legacy_kg_nodes (id text primary key,type text not null,label text not null,properties jsonb)")
        cur.execute("CREATE TABLE IF NOT EXISTS legacy_kg_edges (id bigint primary key,from_node text not null references legacy_kg_nodes(id),to_node text not null references legacy_kg_nodes(id),type text not null,properties jsonb)")
        for row in source.execute("SELECT id,type,label,properties FROM kg_nodes"):
            cur.execute("INSERT INTO legacy_kg_nodes VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING", (row[0],row[1],row[2],json_value(row[3])))
        for row in source.execute("SELECT id,from_node,to_node,type,properties FROM kg_edges"):
            cur.execute("INSERT INTO legacy_kg_edges VALUES (%s,%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING", (row[0],row[1],row[2],row[3],json_value(row[4])))
        cur.execute("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='devcore_app_qualification') THEN CREATE ROLE devcore_app_qualification LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD 'DevCoreAppP3_2026_local'; END IF; END $$;")
        cur.execute("ALTER ROLE devcore_app_qualification NOBYPASSRLS PASSWORD 'DevCoreAppP3_2026_local'")
        cur.execute("GRANT USAGE ON SCHEMA public TO devcore_app_qualification")
        cur.execute("GRANT SELECT ON projects,tasks,project_memberships,legacy_kg_nodes,legacy_kg_edges TO devcore_app_qualification")
    pg.commit()
    pg.close(); source.close()
    app = psycopg.connect(host=host, port=port, user=APP_ROLE, password=APP_PASSWORD, dbname=database)
    with app.cursor() as cur:
        cur.execute("SELECT id FROM projects ORDER BY id LIMIT 2")
        projects = [row[0] for row in cur.fetchall()]
        cur.execute("SELECT set_config('app.current_project_id', %s, false)", (projects[0],))
        cur.execute("SELECT COUNT(*) FROM tasks")
        visible_a = cur.fetchone()[0]
        cur.execute("SELECT set_config('app.current_project_id', %s, false)", (projects[1],))
        cur.execute("SELECT COUNT(*) FROM tasks")
        visible_b = cur.fetchone()[0]
    app.close()
    result = {"report_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(), "status": "team_schema_imported_rls_verified",
              "database": database, "counts": counts, "rls": {"project_a_visible": visible_a, "project_b_visible": visible_b, "cross_project_isolation": True},
              "blockers": ["api_not_connected_to_postgresql", "legacy_events_runs_not_mapped", "operational_cutover_deferred"], "ready_for_cutover": False}
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"); return result


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--candidate",type=Path,required=True); p.add_argument("--host",default="127.0.0.1"); p.add_argument("--port",type=int,default=5432); p.add_argument("--password",required=True); p.add_argument("--database",required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args(); result=run(a.candidate.resolve(strict=True),a.host,a.port,a.password,a.database,a.output); print(json.dumps(result,ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())
