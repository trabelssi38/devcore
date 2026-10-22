"""Cold-start index checks remain mandatory and fail before launching children."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest


def load(monkeypatch, tmp_path):
    for key in ("DEVCORE_LOCAL_ROOT", "DEVCORE_DATA_ROOT", "DEVCORE_PLATFORM_ROOT"):
        monkeypatch.setenv(key, str(tmp_path / key))
    path = Path(__file__).resolve().parents[1] / "Scripts/global_postgres_stack.py"
    spec = importlib.util.spec_from_file_location("stack_index_preflight", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.subprocess, "check_output", lambda args, **kw:
                        "head123" if "rev-parse" in args else "")
    return module


def test_cold_status_still_rejects_stale_index(monkeypatch, tmp_path):
    module = load(monkeypatch, tmp_path)
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw:
        SimpleNamespace(returncode=0, stdout=json.dumps({"indexed": True, "state": {"last_sync_commit": "older"}})))
    with pytest.raises(RuntimeError, match="not aligned"):
        module._repowise_fresh("repowise")


def test_cold_status_timeout_is_explicit_and_bounded(monkeypatch, tmp_path):
    module = load(monkeypatch, tmp_path)
    def timeout(args, **kw):
        assert kw["timeout"] == 300
        raise module.subprocess.TimeoutExpired(args, kw["timeout"])
    monkeypatch.setattr(module.subprocess, "run", timeout)
    with pytest.raises(RuntimeError, match="no global component was started"):
        module._repowise_fresh("repowise")


def test_cold_status_accepts_only_current_index(monkeypatch, tmp_path):
    module = load(monkeypatch, tmp_path)
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw:
        SimpleNamespace(returncode=0, stdout=json.dumps({"indexed": True, "state": {"last_sync_commit": "head123"}})))
    assert module._repowise_fresh("repowise")["indexed_commit"] == "head123"


def test_cold_status_retries_transient_failure_before_children(monkeypatch, tmp_path):
    module = load(monkeypatch, tmp_path)
    calls = []
    def status(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            return SimpleNamespace(returncode=1, stdout="", stderr="temporary failure")
        return SimpleNamespace(returncode=0,
            stdout=json.dumps({"indexed": True, "state": {"last_sync_commit": "head123"}}), stderr="")
    sleeps = []
    monkeypatch.setattr(module.subprocess, "run", status)
    monkeypatch.setattr(module.time, "sleep", sleeps.append)
    assert module._repowise_fresh("repowise")["indexed_commit"] == "head123"
    assert len(calls) == 2
    assert sleeps == [10]


def test_cold_status_reports_persistent_failure(monkeypatch, tmp_path):
    module = load(monkeypatch, tmp_path)
    calls = []
    def status(*args, **kwargs):
        calls.append(1)
        return SimpleNamespace(returncode=1, stdout="", stderr="index unavailable")
    monkeypatch.setattr(module.subprocess, "run", status)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    with pytest.raises(RuntimeError, match="failed three times.*index unavailable"):
        module._repowise_fresh("repowise")
    assert len(calls) == 3
