"""Validate the materialized SQLite candidate before PostgreSQL qualification."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def validate(candidate: Path, output: Path) -> dict:
    with sqlite3.connect(candidate) as db:
        db.execute("PRAGMA foreign_keys=ON")
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        fk = len(db.execute("PRAGMA foreign_key_check").fetchall())
        orphan_tasks = db.execute("SELECT COUNT(*) FROM tasks t LEFT JOIN projects p ON p.id=t.project_id WHERE p.id IS NULL").fetchone()[0]
        project_reviews = db.execute("SELECT COUNT(*) FROM fusion_project_merge_map WHERE status LIKE '%review%'").fetchone()[0]
        task_reviews = db.execute("SELECT COUNT(*) FROM fusion_task_merge_map WHERE status LIKE '%review%'").fetchone()[0]
        counts = {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("projects", "tasks", "kg_nodes", "kg_edges")}
        quarantine = db.execute("SELECT COUNT(*) FROM fusion_graph_quarantine_preview").fetchone()[0]
    blockers = []
    if integrity != "ok" or fk or orphan_tasks: blockers.append("sqlite_constraints_invalid")
    if project_reviews or task_reviews: blockers.append("review_items_remaining")
    result = {"report_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
              "status": "sqlite_candidate_qualified" if not blockers else "sqlite_candidate_failed",
              "candidate": str(candidate.resolve()), "integrity_check": integrity,
              "foreign_key_check": {"total": fk}, "orphan_tasks": orphan_tasks,
              "project_review_required": project_reviews, "task_review_required": task_reviews,
              "counts": counts, "quarantine_edges": quarantine, "blockers": blockers,
              "ready_for_cutover": False}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--candidate", type=Path, required=True); p.add_argument("--output", type=Path, required=True); a = p.parse_args()
    result = validate(a.candidate.resolve(strict=True), a.output); print(json.dumps(result, ensure_ascii=False)); return 0 if not result["blockers"] else 2


if __name__ == "__main__": raise SystemExit(main())
