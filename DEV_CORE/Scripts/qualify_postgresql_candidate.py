"""Copy five legacy tables into an isolated PostgreSQL compatibility sample.

This is not the DevCore team schema migration or a cutover qualification.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import psycopg


def json_value(value):
    if value is None or value == "":
        return "{}"
    try:
        json.loads(value)
        return value
    except (TypeError, json.JSONDecodeError):
        return json.dumps({"source_text": str(value)}, ensure_ascii=False)


def copy_rows(sqlite: sqlite3.Connection, pg: psycopg.Connection, table: str, columns: list[str]) -> int:
    query = f"SELECT {', '.join(columns)} FROM {table}"
    with pg.cursor() as cur:
        with cur.copy(f"COPY {table} ({', '.join(columns)}) FROM STDIN") as copy:
            count = 0
            for row in sqlite.execute(query):
                values = list(row)
                for index, column in enumerate(columns):
                    if column in {"metadata", "properties", "payload"}:
                        values[index] = json_value(values[index])
                copy.write_row(tuple(values))
                count += 1
    return count


def qualify(candidate: Path, host: str, port: int, user: str, password: str, database: str, output: Path) -> dict:
    if not database.startswith("devcore_qualification_"):
        raise ValueError("database must be a new devcore_qualification_* sample")
    sqlite = sqlite3.connect(f"file:{candidate.resolve().as_posix()}?mode=ro&immutable=1", uri=True)
    admin = psycopg.connect(host=host, port=port, user=user, password=password, dbname="postgres", autocommit=True)
    with admin.cursor() as cur:
        cur.execute(f'CREATE DATABASE "{database}"')
    admin.close()
    pg = psycopg.connect(host=host, port=port, user=user, password=password, dbname=database)
    with pg.cursor() as cur:
        cur.execute("CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, root_path TEXT NOT NULL, status TEXT NOT NULL, metadata JSONB NOT NULL, created_at TEXT, updated_at TEXT)")
        cur.execute("CREATE TABLE tasks (id TEXT NOT NULL, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, title TEXT NOT NULL, mode TEXT NOT NULL, status TEXT NOT NULL, steps_done INTEGER NOT NULL, steps_total INTEGER NOT NULL, depends_on TEXT, worktree TEXT, metadata JSONB NOT NULL, created_at TEXT, started_at TEXT, completed_at TEXT, updated_at TEXT, PRIMARY KEY (id, project_id), CHECK (steps_done >= 0 AND steps_done <= steps_total))")
        cur.execute("CREATE TABLE kg_nodes (id TEXT PRIMARY KEY, type TEXT NOT NULL, label TEXT NOT NULL, properties JSONB)")
        cur.execute("CREATE TABLE kg_edges (id BIGINT PRIMARY KEY, from_node TEXT NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE, to_node TEXT NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE, type TEXT NOT NULL, properties JSONB)")
        cur.execute("CREATE TABLE bus_events (id TEXT PRIMARY KEY, source TEXT NOT NULL, event_type TEXT NOT NULL, project TEXT, task_id TEXT, correlation_id TEXT, payload JSONB NOT NULL, created_at TEXT)")
    counts = {}
    counts["projects"] = copy_rows(sqlite, pg, "projects", ["id", "name", "root_path", "status", "metadata", "created_at", "updated_at"])
    counts["tasks"] = copy_rows(sqlite, pg, "tasks", ["id", "project_id", "title", "mode", "status", "steps_done", "steps_total", "depends_on", "worktree", "metadata", "created_at", "started_at", "completed_at", "updated_at"])
    counts["kg_nodes"] = copy_rows(sqlite, pg, "kg_nodes", ["id", "type", "label", "properties"])
    counts["kg_edges"] = copy_rows(sqlite, pg, "kg_edges", ["id", "from_node", "to_node", "type", "properties"])
    counts["bus_events"] = copy_rows(sqlite, pg, "bus_events", ["id", "source", "event_type", "project", "task_id", "correlation_id", "payload", "created_at"])
    pg.commit()
    with pg.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM tasks t LEFT JOIN projects p ON p.id=t.project_id WHERE p.id IS NULL")
        orphan_tasks = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM kg_edges e LEFT JOIN kg_nodes a ON a.id=e.from_node LEFT JOIN kg_nodes b ON b.id=e.to_node WHERE a.id IS NULL OR b.id IS NULL")
        orphan_edges = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM projects")
        project_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tasks")
        task_count = cur.fetchone()[0]
    pg.close(); sqlite.close()
    result = {"report_version": 2, "created_utc": datetime.now(timezone.utc).isoformat(), "status": "legacy_subset_copy_verified",
              "database": database, "host": host, "port": port, "counts": counts, "project_count": project_count,
              "task_count": task_count, "orphan_tasks": orphan_tasks, "orphan_edges": orphan_edges,
              "ready_for_cutover": False, "blockers": ["team_schema_not_applied", "rls_not_qualified", "api_not_connected_to_postgresql", "historical_data_not_fully_imported", "operational_cutover_deferred"],
              "policy": "five-table compatibility sample only; no live application database modified"}
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--candidate", type=Path, required=True); p.add_argument("--host", default="127.0.0.1"); p.add_argument("--port", type=int, default=5432); p.add_argument("--user", default="postgres"); p.add_argument("--database", required=True); p.add_argument("--output", type=Path, required=True); a = p.parse_args()
    result = qualify(a.candidate.resolve(strict=True), a.host, a.port, a.user, os.environ.get("PGPASSWORD", ""), a.database, a.output); print(json.dumps(result, ensure_ascii=False)); return 0 if not result["orphan_tasks"] and not result["orphan_edges"] else 2


if __name__ == "__main__": raise SystemExit(main())
