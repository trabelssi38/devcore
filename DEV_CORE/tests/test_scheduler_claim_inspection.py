"""Read-only diagnosis on isolated SQLite fixtures, including the CLI."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

SCHEDULER = Path(__file__).resolve().parents[1] / "Scheduler"
sys.path.insert(0, str(SCHEDULER))
from inspect_claims import inspect_claims
import scheduler_history


def fixture_db(tmp_path):
    path = tmp_path / "history # fixture.db"
    for number, status in enumerate(("running", "ok", "error", "skipped", "running")):
        assert scheduler_history.record_run(str(number), "date", "started", 0, status,
            error="é" * 3000, db_path=path)
    return path


def test_pages_exclude_completed_and_preserve_database(tmp_path):
    path = fixture_db(tmp_path)
    before = path.read_bytes()
    listing = sorted(p.name for p in tmp_path.iterdir())
    page = inspect_claims(path, limit=2)
    assert [r["id"] for r in page["claims"]] == [1, 3]
    assert page["has_more"] and page["next_after_id"] == 3
    assert page["claims"][0]["truncated_fields"] == ["error"]
    assert len(page["claims"][0]["error"]) == 1024
    last = inspect_claims(path, limit=2, after_id=3)
    assert [r["id"] for r in last["claims"]] == [5]
    assert not last["has_more"] and last["next_after_id"] is None
    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == listing


@pytest.mark.parametrize("kwargs", [{"limit": 0}, {"limit": 101}, {"limit": True},
    {"after_id": -1}, {"after_id": 2**63}, {"after_id": False}])
def test_invalid_bounds_do_not_create_database(tmp_path, kwargs):
    path = tmp_path / "absent" / "history.db"
    with pytest.raises(ValueError):
        inspect_claims(path, **kwargs)
    assert not path.parent.exists()


def test_missing_database_never_created(tmp_path):
    with pytest.raises(FileNotFoundError):
        inspect_claims(tmp_path / "absent" / "history.db")
    assert list(tmp_path.iterdir()) == []


def test_wal_refused_without_sqlite_side_effects(tmp_path):
    path = fixture_db(tmp_path)
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(ValueError, match="WAL database unsupported"):
        inspect_claims(path)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_cli_isolated_mode_and_invalid_schema(tmp_path):
    path = fixture_db(tmp_path)
    before = path.read_bytes()
    command = [sys.executable, "-I", str(SCHEDULER / "inspect_claims.py"), "--database", str(path)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert len(json.loads(result.stdout)["claims"]) == 3
    assert path.read_bytes() == before
    broken = tmp_path / "wrong.db"
    with sqlite3.connect(broken) as conn:
        conn.execute("CREATE TABLE unrelated (id INTEGER)")
    before = broken.read_bytes()
    result = subprocess.run(command[:-1] + [str(broken)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 1 and "no such table" in json.loads(result.stderr)["error"]
    assert not result.stdout and broken.read_bytes() == before
