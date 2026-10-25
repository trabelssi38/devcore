"""Materialize task-project FK repair proposals in a small review database."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _read(path: Path, query: str) -> list[dict]:
    with sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(query)]


def build(current_db: Path, other_db: Path, output_db: Path) -> dict:
    if output_db.exists():
        raise FileExistsError(output_db)
    projects = _read(current_db, "SELECT id, name, root_path, status, metadata FROM projects ORDER BY id")
    other_projects = {row["id"]: row for row in _read(other_db, "SELECT id, name, root_path, status, metadata FROM projects")}
    tasks = _read(current_db, "SELECT id, project_id, title, status, steps_done, steps_total FROM tasks ORDER BY project_id, id")
    project_ids = {row["id"] for row in projects}
    missing_ids = sorted({row["project_id"] for row in tasks if row["project_id"] not in project_ids})
    for project_id in missing_ids:
        if project_id in other_projects:
            row = other_projects[project_id]
            decision = "merge_project_from_other_source"
            evidence = "other_source_project"
            provisional = 0
        else:
            row = {"id": project_id, "name": project_id, "root_path": None, "status": "needs_review", "metadata": "{\"provisional\":true}"}
            decision = "create_provisional_project_needs_review"
            evidence = "missing_on_both_sources"
            provisional = 1
        projects.append({**row, "provisional": provisional, "decision": decision, "evidence": evidence})
    output_db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(output_db) as target:
        target.executescript("""
            CREATE TABLE repair_manifest (created_utc TEXT NOT NULL, status TEXT NOT NULL,
                                          source_current TEXT NOT NULL, source_other TEXT NOT NULL,
                                          automatic_write_allowed INTEGER NOT NULL CHECK(automatic_write_allowed=0));
            CREATE TABLE projects_fk_preview (id TEXT PRIMARY KEY, name TEXT NOT NULL,
                root_path TEXT, status TEXT NOT NULL, metadata TEXT, provisional INTEGER NOT NULL,
                decision TEXT NOT NULL, evidence TEXT NOT NULL);
            CREATE TABLE tasks_fk_preview (id TEXT NOT NULL, original_project_id TEXT NOT NULL,
                proposed_project_id TEXT NOT NULL, title TEXT NOT NULL, status TEXT NOT NULL,
                steps_done INTEGER NOT NULL, steps_total INTEGER NOT NULL, decision TEXT NOT NULL,
                PRIMARY KEY (original_project_id, id));
        """)
        target.execute("INSERT INTO repair_manifest VALUES (?, 'preview_only', ?, ?, 0)", (
            datetime.now(timezone.utc).isoformat(), str(current_db.resolve()), str(other_db.resolve())
        ))
        project_rows = [(p["id"], p.get("name") or p["id"], p.get("root_path"), p.get("status") or "needs_review", p.get("metadata") or "{}", int(p.get("provisional", 0)), p.get("decision", "existing"), p.get("evidence", "current_source")) for p in projects]
        target.executemany("INSERT INTO projects_fk_preview VALUES (?, ?, ?, ?, ?, ?, ?, ?)", project_rows)
        missing = set(missing_ids)
        task_rows = []
        for task in tasks:
            original = str(task["project_id"])
            if original not in missing:
                proposed, decision = original, "unchanged"
            elif original in other_projects:
                proposed, decision = original, "project_from_other_source_needs_review"
            else:
                proposed, decision = original, "provisional_project_needs_review"
            task_rows.append((task["id"], original, proposed, task["title"] or "", task["status"] or "", task["steps_done"] or 0, task["steps_total"] or 0, decision))
        target.executemany("INSERT INTO tasks_fk_preview VALUES (?, ?, ?, ?, ?, ?, ?, ?)", task_rows)
        target.commit()
        integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
        missing_after = target.execute("SELECT COUNT(*) FROM tasks_fk_preview t LEFT JOIN projects_fk_preview p ON p.id=t.proposed_project_id WHERE p.id IS NULL").fetchone()[0]
    return {"output": str(output_db), "status": "preview_only", "projects": len(project_rows), "tasks": len(task_rows), "missing_before": len(missing_ids) and sum(1 for task in tasks if task["project_id"] in missing_ids) or 0, "missing_after": missing_after, "integrity": integrity, "created_utc": datetime.now(timezone.utc).isoformat()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-db", type=Path, required=True)
    parser.add_argument("--other-db", type=Path, required=True)
    parser.add_argument("--output-db", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.current_db, args.other_db, args.output_db)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
