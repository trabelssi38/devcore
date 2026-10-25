"""Build reviewable project/task correspondence tables from two SQLite sources.

Both inputs are opened read-only.  The output is a new SQLite database that
contains mappings and conflicts only; it is never used as an application DB.
No source value is selected as the winner for a conflict.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _connect_readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True)


def _rows(connection: sqlite3.Connection, table: str) -> list[dict[str, object]]:
    connection.row_factory = sqlite3.Row
    return [dict(row) for row in connection.execute(f'SELECT * FROM "{table}"')]


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _project_maps(current: list[dict[str, object]], other: list[dict[str, object]]) -> list[tuple]:
    left = {str(row["id"]): row for row in current}
    right = {str(row["id"]): row for row in other}
    result = []
    for project_id in sorted(left.keys() | right.keys()):
        lrow, rrow = left.get(project_id), right.get(project_id)
        if lrow and rrow:
            changed = sorted(key for key in set(lrow) | set(rrow) if lrow.get(key) != rrow.get(key))
            status = "same_id_review" if changed else "same_id_equal"
        elif lrow:
            changed, status = [], "current_only"
        else:
            changed, status = [], "other_only"
        result.append((
            project_id,
            project_id if lrow and rrow else None,
            status,
            _json(changed),
            _json(lrow),
            _json(rrow),
        ))
    return result


def _task_maps(current: list[dict[str, object]], other: list[dict[str, object]]) -> tuple[list[tuple], list[tuple]]:
    left = {(str(row["project_id"]), str(row["id"])): row for row in current}
    right = {(str(row["project_id"]), str(row["id"])): row for row in other}
    mapping, conflicts = [], []
    review_fields = {"title", "status", "steps_done", "steps_total", "depends_on", "metadata", "worktree"}
    for project_id, task_id in sorted(left.keys() | right.keys()):
        lrow, rrow = left.get((project_id, task_id)), right.get((project_id, task_id))
        if lrow and rrow:
            changed = sorted(key for key in set(lrow) | set(rrow) if lrow.get(key) != rrow.get(key))
            material = sorted(set(changed) & review_fields)
            status = "shared_review" if material else "shared_timestamp_or_equal"
            source_status = "both"
        elif lrow:
            changed, material, status, source_status = [], [], "current_only", "current"
        else:
            changed, material, status, source_status = [], [], "other_only", "other"
        mapping.append((project_id, task_id, status, source_status, _json(changed), _json(lrow), _json(rrow)))
        for field in material:
            conflicts.append((project_id, task_id, field, _json(lrow.get(field)), _json(rrow.get(field)), "review_required"))
    return mapping, conflicts


def build_maps(current_db: Path, other_db: Path, output_db: Path) -> dict[str, object]:
    if output_db.exists():
        raise FileExistsError(output_db)
    with _connect_readonly(current_db) as current, _connect_readonly(other_db) as other:
        projects = _project_maps(_rows(current, "projects"), _rows(other, "projects"))
        tasks, conflicts = _task_maps(_rows(current, "tasks"), _rows(other, "tasks"))
    output_db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(output_db) as target:
        target.executescript("""
            CREATE TABLE fusion_run (created_utc TEXT NOT NULL, current_db TEXT NOT NULL,
                                     other_db TEXT NOT NULL, status TEXT NOT NULL);
            CREATE TABLE project_merge_map (
                source_project_id TEXT PRIMARY KEY, target_project_id TEXT,
                status TEXT NOT NULL, changed_fields TEXT NOT NULL,
                current_row TEXT, other_row TEXT
            );
            CREATE TABLE task_merge_map (
                project_id TEXT NOT NULL, task_id TEXT NOT NULL,
                status TEXT NOT NULL, source_status TEXT NOT NULL,
                changed_fields TEXT NOT NULL, current_row TEXT, other_row TEXT,
                PRIMARY KEY (project_id, task_id)
            );
            CREATE TABLE task_field_conflicts (
                project_id TEXT NOT NULL, task_id TEXT NOT NULL, field TEXT NOT NULL,
                current_value TEXT, other_value TEXT, status TEXT NOT NULL,
                PRIMARY KEY (project_id, task_id, field)
            );
        """)
        target.execute("INSERT INTO fusion_run VALUES (?, ?, ?, 'review_only')", (
            datetime.now(timezone.utc).isoformat(), str(current_db.resolve()), str(other_db.resolve())
        ))
        target.executemany("INSERT INTO project_merge_map VALUES (?, ?, ?, ?, ?, ?)", projects)
        target.executemany("INSERT INTO task_merge_map VALUES (?, ?, ?, ?, ?, ?, ?)", tasks)
        target.executemany("INSERT INTO task_field_conflicts VALUES (?, ?, ?, ?, ?, ?)", conflicts)
        target.commit()
    return {
        "output": str(output_db),
        "status": "review_only",
        "projects": len(projects),
        "tasks": len(tasks),
        "task_field_conflicts": len(conflicts),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-db", type=Path, required=True)
    parser.add_argument("--other-db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_maps(args.current_db, args.other_db, args.output), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
