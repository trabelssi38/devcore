"""Prepare a read-only scheduler history archive for the fusion review."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def prepare(source_db: Path, output_db: Path, jobs_json: Path | None = None) -> dict:
    if output_db.exists():
        raise FileExistsError(output_db)
    source_uri = f"file:{source_db.resolve().as_posix()}?mode=ro&immutable=1"
    with sqlite3.connect(source_uri, uri=True) as source:
        rows = source.execute(
            "SELECT id, job_id, scheduled_at, run_at, duration, status, error, idempotency_key "
            "FROM run_history ORDER BY id"
        ).fetchall()
        integrity = source.execute("PRAGMA integrity_check").fetchone()[0]
    output_db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(output_db) as target:
        target.executescript("""
            CREATE TABLE scheduler_archive_manifest (
                created_utc TEXT NOT NULL, source_db TEXT NOT NULL,
                source_integrity TEXT NOT NULL, status TEXT NOT NULL,
                jobs_activation_allowed INTEGER NOT NULL CHECK(jobs_activation_allowed=0)
            );
            CREATE TABLE run_history_archive (
                source_id INTEGER PRIMARY KEY, job_id TEXT NOT NULL,
                scheduled_at TEXT NOT NULL, run_at TEXT NOT NULL,
                duration REAL NOT NULL, status TEXT NOT NULL, error TEXT,
                idempotency_key TEXT NOT NULL
            );
        """)
        target.execute("INSERT INTO scheduler_archive_manifest VALUES (?, ?, ?, 'archive_only', 0)", (
            datetime.now(timezone.utc).isoformat(), str(source_db.resolve()), integrity
        ))
        target.executemany("INSERT INTO run_history_archive VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
        target.commit()
    jobs_count = None
    if jobs_json and jobs_json.is_file():
        payload = json.loads(jobs_json.read_text(encoding="utf-8"))
        jobs_count = len(payload) if isinstance(payload, list) else len(payload.get("jobs", [])) if isinstance(payload, dict) else None
    return {
        "output": str(output_db), "status": "archive_only", "run_history": len(rows),
        "source_integrity": integrity, "jobs_activation_allowed": False,
        "jobs_json_definitions": jobs_count, "created_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-db", type=Path, required=True)
    parser.add_argument("--output-db", type=Path, required=True)
    parser.add_argument("--jobs-json", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.source_db, args.output_db, args.jobs_json)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
