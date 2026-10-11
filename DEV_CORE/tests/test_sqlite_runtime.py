"""WAL prerequisite checks without accessing application stores."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from Scripts import check_sqlite_runtime as probe


@pytest.mark.parametrize("version,expected", [
    ("3.49.1", False), ("3.51.2", False), ("3.51.3", True),
    ("3.51.4", True), ("3.50.6", False), ("3.50.7", True),
    ("3.50.8", True), ("3.44.5", False), ("3.44.6", True),
    ("3.44.7", True), ("3.45.6", False), ("3.52.0", True),
    ("3.7.0", False), ("3.6.0", False), ("4.0.0", False),
    ("3.51.3-vendor", False), ("3.51", False), (" 3.51.3", False),
    (None, False),
])
def test_upstream_fix_boundaries(version, expected):
    assert probe.wal_reset_fix_known(version) is expected


def test_probe_only_opens_memory_and_closes_connection(monkeypatch):
    original = sqlite3.connect
    connections = []

    def connect(path):
        assert path == ":memory:"
        connection = original(path)
        connections.append(connection)
        return connection

    monkeypatch.setattr(probe.sqlite3, "connect", connect)
    result = probe.inspect_runtime()
    assert result["sqlite_version"] == sqlite3.sqlite_version
    assert result["operationally_qualified"] is False
    assert result["sqlite_source_id"]
    assert result["compile_options"] == sorted(result["compile_options"])
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connections[0].execute("SELECT 1")


def test_cli_uses_current_python_and_never_touches_roots(tmp_path):
    local, data = tmp_path / "local", tmp_path / "data"
    local.mkdir()
    data.mkdir()
    sentinel = local / "devcore.db"
    sentinel.write_bytes(b"not a database - must never be opened")
    result = subprocess.run(
        [sys.executable, str(Path(probe.__file__).resolve())],
        env={**os.environ, "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data)},
        capture_output=True, text=True, encoding="utf-8", timeout=15,
    )
    report = json.loads(result.stdout)
    assert report["sqlite_version"] == sqlite3.sqlite_version
    assert result.returncode == (0 if report["eligible_for_wal_qualification"] else 2)
    assert report["operationally_qualified"] is False
    assert list(local.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"not a database - must never be opened"
    assert list(data.iterdir()) == []
    assert not result.stderr


def test_module_version_mismatch_fails_closed(monkeypatch):
    monkeypatch.setattr(probe.sqlite3, "sqlite_version", "3.999.0")
    result = probe.inspect_runtime()
    assert result["versions_match"] is False
    assert result["eligible_for_wal_qualification"] is False


def test_probe_failure_has_nonzero_exit_and_no_raw_error(monkeypatch, capsys):
    def fail():
        raise sqlite3.OperationalError("private detail")

    monkeypatch.setattr(probe, "inspect_runtime", fail)
    assert probe.main() == 2
    output = capsys.readouterr().out
    assert "private detail" not in output
    assert json.loads(output)["error"] == "sqlite_probe_failed"


def test_fixed_library_without_wal_is_not_eligible(monkeypatch):
    class NoWalConnection:
        def execute(self, sql):
            if sql.startswith("SELECT"):
                return self
            return [("OMIT_WAL",)]

        def fetchone(self):
            return "3.51.3", "fixture source id"

        def close(self):
            pass

    monkeypatch.setattr(probe.sqlite3, "connect", lambda path: NoWalConnection())
    monkeypatch.setattr(probe.sqlite3, "sqlite_version", "3.51.3")
    report = probe.inspect_runtime()
    assert report["wal_reset_fix_known"] is True
    assert report["wal_available"] is False
    assert report["eligible_for_wal_qualification"] is False
