"""Measure read latency on a verified, immutable DevCore SQLite backup."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import statistics
import time
from pathlib import Path

try:
    import sqlite_vec
except ImportError:
    sqlite_vec = None


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _measure(conn: sqlite3.Connection, sql: str, params: tuple, iterations: int) -> dict:
    for _ in range(5):
        conn.execute(sql, params).fetchall()
    samples = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        conn.execute(sql, params).fetchall()
        samples.append((time.perf_counter_ns() - start) / 1_000_000)
    ordered = sorted(samples)
    return {
        "iterations": iterations,
        "p50_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(ordered[math.ceil(0.95 * len(ordered)) - 1], 3),
        "max_ms": round(ordered[-1], 3),
    }


def benchmark(snapshot: Path, iterations: int = 30) -> dict:
    if iterations < 1:
        raise ValueError("iterations must be positive")
    snapshot = snapshot.resolve(strict=True)
    db_path = snapshot / "devcore.db"
    manifest_path = snapshot / "manifest.json"
    if not db_path.is_file() or not manifest_path.is_file():
        raise ValueError("snapshot must contain devcore.db and manifest.json")
    if db_path.with_name("devcore.db-wal").exists():
        raise ValueError("snapshot has a WAL file; immutable read would miss pending pages")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    expected = manifest.get("sqlite", {}).get("sha256")
    if not isinstance(expected, str) or _hash(db_path).lower() != expected.lower():
        raise ValueError("snapshot hash differs from manifest")

    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro&immutable=1", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        if sqlite_vec is not None:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
        project = conn.execute(
            "SELECT project_id, COUNT(*) AS n FROM tasks "
            "GROUP BY project_id ORDER BY n DESC, project_id LIMIT 1"
        ).fetchone()
        if project is None:
            raise ValueError("snapshot has no tasks")
        project_id, task_count = project
        return {
            "snapshot_sha256": expected.lower(),
            "sqlite_bytes": db_path.stat().st_size,
            "project_task_count": task_count,
            "count_by_project": _measure(
                conn, "SELECT COUNT(*) FROM tasks WHERE project_id=?", (project_id,), iterations
            ),
            "board_first_50": _measure(
                conn,
                "SELECT id,status,steps_done FROM tasks WHERE project_id=? "
                "AND status <> 'deleted' ORDER BY created_at ASC LIMIT 50",
                (project_id,), iterations,
            ),
        }
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--iterations", type=int, default=30)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.snapshot, args.iterations), indent=2))
