"""Materialize the user-approved SQLite migration candidate for qualification."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT_APPROVALS = {
    "dashboard_recette_br": r"E:\src_web\dashboard_recette_br",
    "devcore": r"E:\src_python\devcore",
    "pramax_prefs_patch": r"E:\src_python\pramax_prefs_patch",
}


def materialize(base: Path, reviewed: Path, graph: Path, output: Path, report: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(base) as source, sqlite3.connect(output) as db:
        source.backup(db)
        db.execute("PRAGMA foreign_keys=OFF")
        db.execute("ATTACH DATABASE ? AS reviewed", (str(reviewed),))
        db.execute("ATTACH DATABASE ? AS projected", (str(graph),))
        # Copy all review artifacts so provenance and quarantine remain attached.
        for (name,) in db.execute("SELECT name FROM reviewed.sqlite_master WHERE type='table'"):
            if name.startswith("fusion_") and name != "fusion_candidate_manifest":
                db.execute(f'CREATE TABLE "{name}" AS SELECT * FROM reviewed."{name}"')
        db.execute("DROP TABLE IF EXISTS fusion_candidate_manifest")
        db.execute("""CREATE TABLE fusion_candidate_manifest (
            created_utc TEXT NOT NULL, status TEXT NOT NULL, base_source TEXT NOT NULL,
            mapping_source TEXT NOT NULL, graph_source TEXT NOT NULL, scheduler_source TEXT NOT NULL,
            source_sha256_json TEXT NOT NULL, writes_to_application_tables INTEGER NOT NULL,
            decisions_source TEXT NOT NULL, quarantine_policy TEXT NOT NULL)""")
        db.execute("""INSERT INTO fusion_candidate_manifest VALUES (?, 'candidate_qualified_sqlite', ?, '', ?, '', '{}', 1, ?, 'approved_heuristic_with_unresolved_ids_preserved')""",
                   (datetime.now(timezone.utc).isoformat(), str(base.resolve()), str(graph.resolve()), str(reviewed.resolve())))

        # Add every project required by the task FK preview and apply approved roots.
        projects = db.execute("SELECT id, name, root_path, status, metadata, provisional, decision, evidence FROM fusion_projects_fk_preview ORDER BY id").fetchall()
        db.execute("DROP TABLE projects")
        db.execute("""CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, root_path TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active', metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now')), updated_at TEXT NOT NULL DEFAULT (datetime('now')))""")
        old = {row[0]: row for row in source.execute("SELECT id, created_at, updated_at FROM projects")}
        project_rows = []
        for pid, name, root, status, metadata, provisional, decision, evidence in projects:
            root = ROOT_APPROVALS.get(pid, root)
            if not root:
                root = str(Path("E:/DevCoreRuntime/qualification/provisional-projects") / pid)
            try:
                meta = json.loads(metadata or "{}")
                if not isinstance(meta, dict): meta = {"source_metadata": meta}
            except json.JSONDecodeError:
                meta = {"source_metadata": metadata}
            meta["migration_provenance"] = {"decision": decision, "evidence": evidence, "user_approved": True}
            created, updated = old.get(pid, (None, None))[1:] if pid in old else (None, None)
            project_rows.append((pid, name or pid, root, status or "active", json.dumps(meta, ensure_ascii=False), created, updated))
        db.executemany("INSERT INTO projects VALUES (?, ?, ?, ?, ?, COALESCE(?, datetime('now')), COALESCE(?, datetime('now')))", project_rows)

        # Keep current task values, apply approved worktree policy, and preserve provenance.
        tasks = db.execute("SELECT id, project_id, title, mode, status, steps_done, steps_total, depends_on, worktree, metadata, created_at, started_at, completed_at, updated_at FROM tasks").fetchall()
        db.execute("DROP TABLE tasks")
        db.execute("""CREATE TABLE tasks (id TEXT NOT NULL, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            title TEXT NOT NULL, mode TEXT NOT NULL DEFAULT 'coding', status TEXT NOT NULL DEFAULT 'todo',
            steps_done INTEGER NOT NULL DEFAULT 0, steps_total INTEGER NOT NULL DEFAULT 1, depends_on TEXT,
            worktree TEXT, metadata TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT (datetime('now')),
            started_at TEXT, completed_at TEXT, updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (id, project_id), CHECK (steps_done >= 0), CHECK (steps_total >= 1), CHECK (steps_done <= steps_total))""")
        db.executemany("INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       [(a, b, c, d, e, f, g, h, None, (i if isinstance(i, str) else "{}"), j, k, l, m) for a,b,c,d,e,f,g,h,_worktree,i,j,k,l,m in tasks])

        # Replace graph application tables with the integrity-checked projection.
        nodes = db.execute("SELECT id, type, label, properties FROM projected.nodes").fetchall()
        edges = db.execute("SELECT edge_rowid, from_node, to_node, type, properties FROM projected.edges ORDER BY edge_rowid").fetchall()
        db.execute("DROP TABLE kg_edges")
        db.execute("DROP TABLE kg_nodes")
        db.execute("CREATE TABLE kg_nodes (id TEXT PRIMARY KEY, type TEXT NOT NULL, label TEXT NOT NULL, properties TEXT DEFAULT '{}')")
        db.execute("CREATE TABLE kg_edges (id INTEGER PRIMARY KEY AUTOINCREMENT, from_node TEXT NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE, to_node TEXT NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE, type TEXT NOT NULL, properties TEXT DEFAULT '{}')")
        db.executemany("INSERT INTO kg_nodes VALUES (?, ?, ?, ?)", nodes)
        db.executemany("INSERT INTO kg_edges (id, from_node, to_node, type, properties) VALUES (?, ?, ?, ?, ?)", edges)
        db.execute("UPDATE fusion_project_merge_map SET status='resolved_user_approved' WHERE status='same_id_review'")
        db.execute("UPDATE fusion_task_merge_map SET status='resolved_user_approved' WHERE status='shared_review'")
        db.execute("CREATE TABLE migration_decision_provenance (decision TEXT PRIMARY KEY, approved_by TEXT NOT NULL, evidence TEXT NOT NULL)")
        db.executemany("INSERT INTO migration_decision_provenance VALUES (?, ?, ?)", [
            ("project_ownership_and_roots", "user", "migration-decision-approvals-2026-10-12.json"),
            ("task_field_conflict_winners", "user", "migration-decision-approvals-2026-10-12.json"),
            ("quarantine_retention_policy", "user", "graph-heuristic-preview-2026-10-12.json"),
        ])
        db.commit()
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        fk = db.execute("PRAGMA foreign_key_check").fetchall()
        result = {"output": str(output), "status": "candidate_qualified_sqlite", "integrity_check": integrity,
                  "foreign_key_violations": len(fk), "projects": len(project_rows), "tasks": len(tasks),
                  "graph_nodes": len(nodes), "graph_edges": len(edges), "unresolved_graph_edges": db.execute("SELECT COUNT(*) FROM fusion_graph_quarantine_preview").fetchone()[0],
                  "ready_for_cutover": False, "blockers": ["postgresql_global_stack_not_qualified", "operational_cutover_deferred"],
                  "created_utc": datetime.now(timezone.utc).isoformat()}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", type=Path, required=True); p.add_argument("--reviewed", type=Path, required=True)
    p.add_argument("--graph", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True); a = p.parse_args()
    result = materialize(a.base, a.reviewed, a.graph, a.output, a.report)
    print(json.dumps(result, ensure_ascii=False)); return 0 if result["foreign_key_violations"] == 0 else 2


if __name__ == "__main__": raise SystemExit(main())
