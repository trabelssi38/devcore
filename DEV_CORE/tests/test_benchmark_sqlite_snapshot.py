import hashlib
import json
import sqlite3

import pytest

from Scripts.benchmark_sqlite_snapshot import benchmark


def test_benchmark_reads_verified_snapshot_without_writing(tmp_path):
    db = tmp_path / "devcore.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE tasks(id TEXT,project_id TEXT,status TEXT,steps_done INTEGER,created_at TEXT)")
    conn.executemany(
        "INSERT INTO tasks VALUES (?,?,?,?,?)",
        [("T-01", "alpha", "todo", 0, "2026-01-01"),
         ("T-02", "alpha", "done", 1, "2026-01-02")],
    )
    conn.commit()
    conn.close()
    digest = hashlib.sha256(db.read_bytes()).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sqlite": {"sha256": digest}}), encoding="utf-8")

    result = benchmark(tmp_path, iterations=3)

    assert result["project_task_count"] == 2
    assert result["count_by_project"]["iterations"] == 3
    assert result["board_first_50"]["p95_ms"] >= 0
    assert hashlib.sha256(db.read_bytes()).hexdigest() == digest
    assert not (tmp_path / "devcore.db-wal").exists()

    manifest.write_text(json.dumps({"sqlite": {"sha256": "wrong"}}), encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        benchmark(tmp_path)
