"""The old dc.py next command must use SQL and project context."""

import json
import importlib.util
import argparse
import os
import subprocess
import sys
from pathlib import Path

from devcore_engine.services.tasks import TaskService
import pytest


LEGACY_CLI = Path(__file__).resolve().parents[1] / "Scripts" / "dc.py"
PLATFORM_ROOT = LEGACY_CLI.parent.parent


def _env(tmp_path):
    env = os.environ.copy()
    env["DEVCORE_LOCAL_ROOT"] = str(tmp_path / "local")
    env["DEVCORE_DATA_ROOT"] = str(tmp_path / "shared")
    env["DEVCORE_ACTIVE_PROJECT_NAME"] = "beta"
    env["PYTHONPATH"] = str(PLATFORM_ROOT)
    return env


def test_legacy_next_selects_only_local_manifest_project_in_sql(tmp_path, monkeypatch):
    alpha = tmp_path / "alpha"
    manifest = alpha / ".devcore" / "project.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"name": "alpha"}), encoding="utf-8")
    (alpha / "nested").mkdir()
    env = _env(tmp_path)
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", env["DEVCORE_LOCAL_ROOT"])
    monkeypatch.setenv("DEVCORE_DATA_ROOT", env["DEVCORE_DATA_ROOT"])
    service = TaskService()
    service.add_task("alpha task", project_id="alpha")
    service.add_task("beta task", project_id="beta")
    service.conn.close()

    legacy_board = tmp_path / "shared" / "Memory" / "alpha" / "tasks.json"
    legacy_board.parent.mkdir(parents=True)
    legacy_board.write_text("legacy unchanged", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(LEGACY_CLI), "nt"],
        cwd=alpha / "nested", env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "T-01" in result.stdout
    verify = TaskService()
    assert verify.get_task("T-01", "alpha")["status"] == "in_progress"
    assert verify.get_task("T-01", "beta")["status"] == "todo"
    verify.conn.close()
    assert legacy_board.read_text(encoding="utf-8") == "legacy unchanged"

    explicit = subprocess.run(
        [sys.executable, str(LEGACY_CLI), "nt", "--project", "beta"],
        cwd=tmp_path, env=env, capture_output=True, text=True, check=False,
    )
    assert explicit.returncode == 0, explicit.stderr
    verify = TaskService()
    assert verify.get_task("T-01", "beta")["status"] == "in_progress"
    verify.conn.close()
    assert legacy_board.read_text(encoding="utf-8") == "legacy unchanged"


def test_legacy_next_without_project_fails_before_opening_database(tmp_path):
    env = _env(tmp_path)
    result = subprocess.run(
        [sys.executable, str(LEGACY_CLI), "next", "task"],
        cwd=tmp_path, env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert "Project required" in result.stderr
    assert not (tmp_path / "local" / "devcore.db").exists()


def test_legacy_diagnostics_ignore_cached_project_and_reject_foreign_board(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))
    spec = importlib.util.spec_from_file_location("devcore_legacy_dc_test", LEGACY_CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert not (tmp_path / "local").exists()
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "platform").exists()

    alpha = tmp_path / "alpha"
    nested = alpha / "nested"
    nested.mkdir(parents=True)
    manifest = alpha / ".devcore" / "project.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({"name": "alpha"}), encoding="utf-8")
    monkeypatch.chdir(nested)
    monkeypatch.setenv("DEVCORE_ACTIVE_PROJECT_PWD", str(nested))
    monkeypatch.setenv("DEVCORE_ACTIVE_PROJECT_NAME", "beta")
    assert module.get_active_project() == "alpha"
    assert os.environ["DEVCORE_ACTIVE_PROJECT_NAME"] == "beta"

    board_dir = tmp_path / "data" / "Memory" / "alpha"
    board_dir.mkdir(parents=True)
    board = board_dir / "tasks.json"
    board.write_text(json.dumps({"project": "beta", "tasks": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="project mismatch"):
        module.load_scoped_legacy_board(tmp_path / "data", "alpha")
    board.write_text(json.dumps({"project": "alpha", "tasks": []}), encoding="utf-8")
    assert module.load_scoped_legacy_board(tmp_path / "data", "alpha")["project"] == "alpha"

    outsider = tmp_path / "outsider"
    outsider.mkdir()
    monkeypatch.chdir(outsider)
    assert module.get_active_project() is None
    assert module.load_scoped_legacy_board(tmp_path / "data", None) is None


def test_legacy_benchmark_and_profile_leave_data_roots_untouched(tmp_path):
    env = _env(tmp_path)
    env["DEVCORE_PLATFORM_ROOT"] = str(tmp_path / "platform")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    for key in ("TMP", "TEMP", "TMPDIR"):
        env[key] = str(scratch)
    for command in ("benchmark", "profile"):
        result = subprocess.run(
            [sys.executable, str(LEGACY_CLI), command],
            cwd=tmp_path, env=env, capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stderr
        assert not (tmp_path / "local").exists()
        assert not (tmp_path / "shared").exists()
        assert not (tmp_path / "platform").exists()
        assert list(scratch.iterdir()) == []
        if command == "benchmark":
            assert "benchmark_sqlite_snapshot.py" in result.stdout


def test_legacy_doctor_skips_global_conversations_and_reports_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "profile"))
    spec = importlib.util.spec_from_file_location("devcore_legacy_doctor_test", LEGACY_CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "SCRIPT_DIR", tmp_path / "scripts")
    monkeypatch.setattr(module, "DEV_CORE", tmp_path / "platform")
    monkeypatch.setattr(module, "get_platform_title", lambda: "DevCore")
    monkeypatch.setattr(module, "get_active_project", lambda: None)
    monkeypatch.setattr(module, "ping_http", lambda *_: False)
    monkeypatch.setattr(module, "ping_tcp", lambda *_: False)
    legacy = tmp_path / "data" / "Memory" / "conversations.db"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"not a sqlite database")
    local_db = tmp_path / "local" / "devcore.db"
    local_db.parent.mkdir()
    local_db.write_bytes(b"file presence is not vector readiness")
    monkeypatch.setattr(module.sqlite3, "connect", lambda *_args, **_kwargs: pytest.fail("global database opened"))
    assert module.cmd_doctor(argparse.Namespace()) == 1
    output = capsys.readouterr().out
    assert "Base conversations globale non evaluee" in output
    assert "Base SQLite locale presente" in output
    assert "Memoire vectorielle non evaluee" in output
    assert legacy.read_bytes() == b"not a sqlite database"

    monkeypatch.setattr(module, "cmd_doctor", lambda *_: 7)
    monkeypatch.setattr(sys, "argv", ["dc.py", "doctor"])
    with pytest.raises(SystemExit) as result:
        module.main()
    assert result.value.code == 7


def test_legacy_tcp_probe_does_not_change_process_socket_timeout(monkeypatch):
    spec = importlib.util.spec_from_file_location("devcore_legacy_tcp_test", LEGACY_CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    before = module.socket.getdefaulttimeout()
    class Connection:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
    calls = []
    monkeypatch.setattr(module.socket, "create_connection", lambda address, timeout: calls.append((address, timeout)) or Connection())
    assert module.ping_tcp("127.0.0.1", 5432, timeout=0.25)
    assert calls == [(('127.0.0.1', 5432), 0.25)]
    assert module.socket.getdefaulttimeout() == before
