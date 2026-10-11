"""Create a review-only SQLite copy with task row versions.

The source is opened read-only. Run this after FK repair/reconciliation, and
review the candidate before any service cutover.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from devcore_engine.db import TASK_VERSION_TRIGGER_SQL  # noqa: E402

MIGRATION_VERSION = 2


def _digest_tasks(conn: sqlite3.Connection, columns: list[str]) -> str:
    selected = ", ".join(f'"{column}"' for column in columns)
    digest = hashlib.sha256()
    for row in conn.execute(f"SELECT {selected} FROM tasks ORDER BY project_id, id"):
        digest.update(json.dumps(tuple(row), ensure_ascii=False, default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def preview(source_path: Path, destination_path: Path) -> dict:
    source_path = source_path.resolve(strict=True)
    destination_path = destination_path.resolve()
    if source_path == destination_path or destination_path.exists():
        raise ValueError("destination must be a new path distinct from source")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(f"file:{source_path.as_posix()}?mode=ro", uri=True)
    candidate = sqlite3.connect(destination_path)
    try:
        source_version = source.execute("PRAGMA user_version").fetchone()[0]
        if source_version != 1:
            raise RuntimeError(f"expected reconciled SQLite schema version 1, got {source_version}")
        columns = [row[1] for row in source.execute("PRAGMA table_info(tasks)")]
        if "version" in columns:
            raise RuntimeError("tasks already have a version column")
        before_count = source.execute("SELECT count(*) FROM tasks").fetchone()[0]
        before_digest = _digest_tasks(source, columns)
        source.backup(candidate)
        candidate.execute("ALTER TABLE tasks ADD COLUMN version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1)")
        candidate.executescript(TASK_VERSION_TRIGGER_SQL)
        candidate.execute(f"PRAGMA user_version={MIGRATION_VERSION}")
        candidate.commit()
        if (candidate.execute("SELECT count(*) FROM tasks").fetchone()[0] != before_count
                or _digest_tasks(candidate, columns) != before_digest):
            raise RuntimeError("task rows changed during version migration")
        if candidate.execute("SELECT count(*) FROM tasks WHERE version <> 1").fetchone()[0]:
            raise RuntimeError("new task versions are not initialized to 1")
        integrity = candidate.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")
        violations = Counter((row[0], row[2]) for row in candidate.execute("PRAGMA foreign_key_check"))
        return {
            "source": str(source_path),
            "candidate": str(destination_path),
            "source_schema_version": source_version,
            "candidate_schema_version": MIGRATION_VERSION,
            "preserved_tasks": before_count,
            "integrity": integrity,
            "foreign_key_violations": [
                {"table": child, "parent": parent, "count": count}
                for (child, parent), count in sorted(violations.items())
            ],
            "ready_for_cutover": not violations,
        }
    except Exception:
        candidate.close()
        destination_path.unlink(missing_ok=True)
        raise
    finally:
        source.close()
        candidate.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(preview(args.source, args.destination), indent=2, ensure_ascii=False))
