"""Bounded WAL/checkpoint regression on disposable databases, not a bug reproducer."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
import sqlite3
import threading
import time

import pytest

from Scripts.check_sqlite_runtime import inspect_runtime


@pytest.mark.parametrize("checkpoint_mode", ["PASSIVE", "TRUNCATE"])
def test_concurrent_writes_checkpoints_and_backup(tmp_path, checkpoint_mode):
    assert inspect_runtime()["eligible_for_wal_qualification"], "corrected SQLite required"
    path = tmp_path / "qualification.db"
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        connection.executescript(
            "CREATE TABLE counters(project TEXT PRIMARY KEY,n INTEGER NOT NULL);"
            "INSERT INTO counters VALUES('alpha',0),('beta',0);"
            "CREATE TABLE ledger(project TEXT,n INTEGER,payload TEXT,PRIMARY KEY(project,n));"
        )
        connection.commit()
    start = threading.Barrier(5)
    iterations = 40

    def connect():
        # Match DevCore connect_db's busy timeout. FULL commits on this Windows
        # volume may take longer than five seconds for a competing batch.
        connection = sqlite3.connect(path, timeout=30)
        connection.execute("PRAGMA wal_autocheckpoint=0")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def writer(project):
        with closing(connect()) as connection:
            start.wait(timeout=10)
            for n in range(1, iterations + 1):
                with connection:
                    connection.execute("UPDATE counters SET n=n+1 WHERE project=?", (project,))
                    connection.execute("INSERT INTO ledger VALUES(?,?,?)", (project, n, project * 1024))
                time.sleep(0.001)
            return iterations

    def checkpoint():
        busy = 0
        with closing(connect()) as connection:
            start.wait(timeout=10)
            for _ in range(iterations):
                row = connection.execute(f"PRAGMA wal_checkpoint({checkpoint_mode})").fetchone()
                assert row[0] in (0, 1)
                busy += row[0]
                time.sleep(0.001)
        return busy

    def reader():
        with closing(connect()) as connection:
            start.wait(timeout=10)
            for _ in range(iterations):
                connection.execute("BEGIN")
                counts = connection.execute("SELECT project,n FROM counters ORDER BY project").fetchall()
                for project, n in counts:
                    assert connection.execute("SELECT COUNT(*) FROM ledger WHERE project=?", (project,)).fetchone()[0] == n
                connection.rollback()
                time.sleep(0.001)
        return iterations

    elapsed = time.monotonic()
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(writer, "alpha"), pool.submit(writer, "beta"),
                   pool.submit(checkpoint), pool.submit(checkpoint), pool.submit(reader)]
        results = [future.result(timeout=45) for future in futures]
    elapsed = time.monotonic() - elapsed
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] == 0
        expected = [(p, n, p * 1024) for p in ("alpha", "beta") for n in range(1, iterations + 1)]
        assert connection.execute("SELECT * FROM ledger ORDER BY project,n").fetchall() == expected
        assert connection.execute("SELECT * FROM counters ORDER BY project").fetchall() == [("alpha", iterations), ("beta", iterations)]
        with closing(sqlite3.connect(tmp_path / "restored.db")) as target:
            connection.backup(target)
    with closing(sqlite3.connect(tmp_path / "restored.db")) as restored:
        assert restored.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert restored.execute("SELECT * FROM ledger ORDER BY project,n").fetchall() == expected
    print(json.dumps({"mode": checkpoint_mode, "commits": sum(results[:2]),
                      "checkpoint_attempts": iterations * 2, "checkpoint_busy": sum(results[2:4]),
                      "reader_snapshots": results[4], "elapsed_seconds": round(elapsed, 3)}))


def test_devcore_sqlite_vec_and_schema_on_corrected_runtime(tmp_path):
    assert inspect_runtime()["eligible_for_wal_qualification"], "corrected SQLite required"
    from devcore_engine.db import HAS_SQLITE_VEC, connect_db

    assert HAS_SQLITE_VEC, "locked sqlite-vec dependency required"
    with closing(connect_db(tmp_path / "extension.db")) as connection:
        assert connection.execute("SELECT vec_length(vec_f32('[1,2,3]'))").fetchone()[0] == 3
        assert [row[0] for row in connection.execute("PRAGMA integrity_check")] == ["ok"]
