"""Bounded, read-only inspection of unresolved scheduler occurrences.

An unresolved claim is not proof of an orphan or permission to repeat effects.
The database must be explicitly selected; no runtime paths are loaded.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import time


def inspect_claims(db_path: Path, *, limit: int = 50, after_id: int = 0) -> dict:
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer between 1 and 100")
    if type(after_id) is not int or not 0 <= after_id < 2**63 - 1:
        raise ValueError("after_id must be a nonnegative SQLite integer")
    path = Path(db_path).resolve(strict=True)
    if not path.is_file():
        raise ValueError("database must be an existing file")
    # SQLite can create WAL shared-memory sidecars even with mode=ro.
    # This inspector targets the scheduler's DELETE-journal database only.
    with path.open("rb") as stream:
        header = stream.read(100)
    if header[:16] != b"SQLite format 3\x00":
        raise ValueError("not a SQLite database")
    if header[18:20] != b"\x01\x01":
        raise ValueError("WAL database unsupported; use a validated DELETE-journal snapshot")
    # URI encoding from as_uri protects paths containing ? or #.
    conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)
    try:
        conn.execute("PRAGMA query_only=ON")
        deadline = time.monotonic() + 2
        conn.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        conn.row_factory = sqlite3.Row
        # Bound text in SQLite, before copying it into Python. No COUNT scan.
        fields = {"job_id": 256, "scheduled_at": 128, "run_at": 128,
                  "status": 16, "error": 1024, "idempotency_key": 512}
        columns = ["id"]
        for name, cap in fields.items():
            columns.extend([f"substr({name},1,{cap}) AS {name}",
                            f"length({name}) > {cap} AS {name}_truncated"])
        rows = conn.execute(
            "SELECT " + ",".join(columns) + " FROM run_history "
            "WHERE id > ? AND status IN ('running','error') ORDER BY id LIMIT ?",
            (after_id, limit + 1),
        ).fetchall()
        claims = []
        for row in rows[:limit]:
            claim = {name: row[name] for name in ("id", *fields)}
            claim["truncated_fields"] = [name for name in fields if row[name + "_truncated"]]
            claims.append(claim)
        more = len(rows) > limit
        return {"schema_version": 1, "read_only": True, "claims": claims,
                "has_more": more, "next_after_id": claims[-1]["id"] if more else None,
                "warning": "Unresolved does not mean orphaned. Verify effects before any resolution or retry.",
                "consistency": "One query snapshot; subsequent pages may reflect concurrent changes."}
    finally:
        conn.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--after-id", type=int, default=0)
    args = parser.parse_args(argv)
    try:
        result = inspect_claims(args.database, limit=args.limit, after_id=args.after_id)
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
