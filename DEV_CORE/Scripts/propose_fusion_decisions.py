"""Create non-destructive proposals from a fusion mapping database.

The output is a review document.  It never changes a source or the mapping
database and never selects a winning value for a material task conflict.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def propose(mapping_db: Path, output: Path) -> dict:
    uri = f"file:{mapping_db.resolve().as_posix()}?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as connection:
        projects = connection.execute(
            "SELECT source_project_id, target_project_id, status, changed_fields "
            "FROM project_merge_map ORDER BY source_project_id"
        ).fetchall()
        tasks = connection.execute(
            "SELECT project_id, task_id, status, source_status, changed_fields "
            "FROM task_merge_map ORDER BY project_id, task_id"
        ).fetchall()
        conflicts = connection.execute(
            "SELECT project_id, task_id, field, current_value, other_value, status "
            "FROM task_field_conflicts ORDER BY project_id, task_id, field"
        ).fetchall()

    project_proposals = []
    for project_id, target_id, status, changed_fields in projects:
        decision = "review_required" if status == "same_id_review" else status
        project_proposals.append({
            "project_id": project_id,
            "target_project_id": target_id,
            "source_status": status,
            "decision": decision,
            "changed_fields": json.loads(changed_fields),
        })

    task_proposals = []
    for project_id, task_id, status, source_status, changed_fields in tasks:
        if status == "shared_review":
            decision = "review_required"
        elif status == "shared_timestamp_or_equal":
            decision = "preserve_content_and_record_timestamp_provenance"
        else:
            decision = status
        task_proposals.append({
            "project_id": project_id,
            "task_id": task_id,
            "source_status": source_status,
            "mapping_status": status,
            "decision": decision,
            "changed_fields": json.loads(changed_fields),
        })

    conflict_rows = [
        {
            "project_id": project_id,
            "task_id": task_id,
            "field": field,
            "current_value": json.loads(current_value) if current_value else None,
            "other_value": json.loads(other_value) if other_value else None,
            "decision": "review_required",
        }
        for project_id, task_id, field, current_value, other_value, _status in conflicts
    ]
    report = {
        "report_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_mapping": str(mapping_db.resolve()),
        "status": "proposal_only",
        "policy": {
            "material_fields": ["title", "status", "steps_done", "steps_total", "depends_on", "metadata", "worktree"],
            "timestamps": "preserve_provenance_and_review_if_needed",
            "no_source_mutation": True,
        },
        "counts": {
            "projects": len(project_proposals),
            "project_review_required": sum(x["decision"] == "review_required" for x in project_proposals),
            "tasks": len(task_proposals),
            "task_review_required": sum(x["decision"] == "review_required" for x in task_proposals),
            "field_conflicts": len(conflict_rows),
            "field_conflicts_by_name": dict(Counter(x["field"] for x in conflict_rows)),
        },
        "projects": project_proposals,
        "tasks": task_proposals,
        "field_conflicts": conflict_rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"output": str(output), "status": "proposal_only", "counts": report["counts"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping-db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(propose(args.mapping_db, args.output), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
