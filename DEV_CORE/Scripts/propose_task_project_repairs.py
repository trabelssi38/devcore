"""Propose repairs for tasks whose project foreign key is missing."""

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


def propose(current_db: Path, other_db: Path, output: Path) -> dict:
    current_projects = {row["id"]: row for row in _read(current_db, "SELECT * FROM projects")}
    other_projects = {row["id"]: row for row in _read(other_db, "SELECT * FROM projects")}
    missing = _read(
        current_db,
        "SELECT t.project_id, t.id, t.title FROM tasks t LEFT JOIN projects p ON p.id=t.project_id "
        "WHERE p.id IS NULL ORDER BY t.project_id, t.id",
    )
    grouped: dict[str, list[dict]] = {}
    for task in missing:
        grouped.setdefault(str(task["project_id"]), []).append(task)
    proposals = []
    for project_id, tasks in sorted(grouped.items()):
        if project_id in other_projects:
            decision, evidence = "merge_project_from_other_source", "project_exists_on_other_source"
            project_row = other_projects[project_id]
        else:
            decision, evidence = "create_provisional_project_needs_review", "project_missing_on_both_sources"
            project_row = None
        proposals.append({
            "project_id": project_id,
            "task_count": len(tasks),
            "task_ids": [task["id"] for task in tasks],
            "decision": decision,
            "evidence": evidence,
            "other_project": project_row,
        })
    report = {
        "report_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "proposal_only",
        "current_projects": len(current_projects),
        "other_projects": len(other_projects),
        "missing_task_rows": len(missing),
        "proposals": proposals,
        "policy": "no project row is created or task project_id changed automatically",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"output": str(output), "status": "proposal_only", "missing_task_rows": len(missing), "proposals": len(proposals)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-db", type=Path, required=True)
    parser.add_argument("--other-db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(propose(args.current_db, args.other_db, args.output), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
