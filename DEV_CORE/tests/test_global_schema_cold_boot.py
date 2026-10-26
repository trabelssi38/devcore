"""Cold-boot schema gating retries connection failures but refuses drift."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired


def _launcher(monkeypatch, tmp_path):
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))
    script = Path(__file__).resolve().parents[1] / "Scripts" / "run_global_postgres_stack.py"
    spec = importlib.util.spec_from_file_location("global_launcher_schema_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_schema_waits_for_postgres_then_succeeds(monkeypatch, tmp_path):
    launcher = _launcher(monkeypatch, tmp_path)
    calls = iter([TimeoutExpired("schema", 20),
                  CompletedProcess([], 1, '{"status":"global_schema_check_failed"}', ""),
                  CompletedProcess([], 0, '{"status":"global_schema_ready"}', "")])
    pauses = []

    def run(*args, **kwargs):
        item = next(calls)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(launcher.subprocess, "run", run)
    monkeypatch.setattr(launcher.time, "sleep", pauses.append)
    code, output, attempts = launcher._check_schema(
        tmp_path / "python.exe", tmp_path / "check.py", tmp_path / "config.json",
        tmp_path, {})
    assert (code, output, attempts) == (0, '{"status":"global_schema_ready"}', 3)
    assert pauses == [5, 5]


def test_schema_mismatch_fails_immediately(monkeypatch, tmp_path):
    launcher = _launcher(monkeypatch, tmp_path)
    monkeypatch.setattr(launcher.subprocess, "run", lambda *a, **k:
                        CompletedProcess([], 2, '{"status":"global_schema_missing"}', ""))
    monkeypatch.setattr(launcher.time, "sleep", lambda _: (_ for _ in ()).throw(
        AssertionError("schema mismatch must not retry")))
    assert launcher._check_schema(tmp_path / "python.exe", tmp_path / "check.py",
                                  tmp_path / "config.json", tmp_path, {}) == (
                                      2, '{"status":"global_schema_missing"}', 1)
