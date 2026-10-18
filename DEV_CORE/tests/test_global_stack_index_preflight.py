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
        SimpleNamespace(stdout=json.dumps({"indexed": True, "state": {"last_sync_commit": "older"}})))
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
        SimpleNamespace(stdout=json.dumps({"indexed": True, "state": {"last_sync_commit": "head123"}})))
    assert module._repowise_fresh("repowise")["indexed_commit"] == "head123"
