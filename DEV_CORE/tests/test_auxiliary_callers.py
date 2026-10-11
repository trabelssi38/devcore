"""Auxiliary caller and child environment isolation; disposable inputs only."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

PLATFORM = Path(__file__).resolve().parents[1]


def load_compactor(tmp_path, monkeypatch):
    for key, leaf in (("DEVCORE_PLATFORM_ROOT", "platform"), ("DEVCORE_LOCAL_ROOT", "local"), ("DEVCORE_DATA_ROOT", "data")):
        monkeypatch.setenv(key, str(tmp_path / leaf))
    spec = importlib.util.spec_from_file_location("fixture_compactor", PLATFORM / "Scripts/Auto/memory_compactor.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_compactor_is_explicit_auxiliary_and_ignores_native_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_ROUTER_URL", "https://example.invalid/native")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:8787/v1")
    module = load_compactor(tmp_path, monkeypatch)
    calls, handlers = [], []
    result = b'{"choices":[{"message":{"content":"- [score: 0.8] retained fixture"}}]}'
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size):
            assert size == 1024 * 1024 + 1
            return result
    def open(request, timeout):
        calls.append(request)
        assert timeout == 30
        return Response()
    def build(*items):
        handlers.extend(items)
        return SimpleNamespace(open=open)
    monkeypatch.setattr(module.urllib.request, "build_opener", build)
    assert module.call_llm_compaction("fixture", ["- original"]) == ["- [score: 0.8] retained fixture"]
    request = calls[0]
    assert request.full_url == "http://127.0.0.1:8789/v1/chat/completions"
    body = json.loads(request.data)
    assert body["model"] == "devcore-summary" and body["task_type"] == "summary"
    assert body["fallback_providers"] == []
    assert handlers[0].proxies == {}
    assert handlers[1].redirect_request(None, None, 302, "", {}, "https://example.invalid") is None
    assert not (tmp_path / "data").exists()


@pytest.mark.parametrize("failure", ["unavailable", "oversized", "invalid"])
def test_compactor_preserves_original_on_failure(tmp_path, monkeypatch, failure):
    module = load_compactor(tmp_path, monkeypatch)
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size):
            return b"x" * size if failure == "oversized" else b"invalid json"
    def open(*args, **kwargs):
        if failure == "unavailable": raise OSError("fixture offline")
        return Response()
    monkeypatch.setattr(module.urllib.request, "build_opener", lambda *a: SimpleNamespace(open=open))
    original = ["- fixture decision preserved"]
    assert module.call_llm_compaction("fixture", original) is original
    assert not (tmp_path / "data").exists()


def test_compactor_requires_project_and_keeps_lessons_and_backup_project_scoped(tmp_path, monkeypatch):
    module = load_compactor(tmp_path, monkeypatch)
    alpha = tmp_path / "data" / "Memory" / "alpha" / "LESSONS.md"
    beta = tmp_path / "data" / "Memory" / "beta" / "LESSONS.md"
    alpha.parent.mkdir(parents=True)
    beta.parent.mkdir(parents=True)
    alpha.write_text("# Alpha\n\n## Workflow\n- alpha lesson\n", encoding="utf-8")
    beta_text = "# Beta\n\n## Workflow\n- beta lesson\n"
    beta.write_text(beta_text, encoding="utf-8")

    module.compact_lessons_file("alpha")

    backups = list((alpha.parent / "archive").glob("LESSONS_pre_compaction_*.md"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "# Alpha\n\n## Workflow\n- alpha lesson\n"
    assert "alpha lesson" in alpha.read_text(encoding="utf-8")
    assert beta.read_text(encoding="utf-8") == beta_text
    assert not (tmp_path / "data" / "Memory" / "LESSONS.md").exists()


def test_compactor_cli_requires_project_before_data_access(tmp_path, monkeypatch):
    module = load_compactor(tmp_path, monkeypatch)
    with pytest.raises(SystemExit) as error:
        module.main([])
    assert error.value.code == 2
    assert not (tmp_path / "data").exists()


@pytest.mark.parametrize("project", ["", "../beta", "alpha/beta", "C:beta"])
def test_compactor_rejects_invalid_project_before_writing(tmp_path, monkeypatch, project):
    module = load_compactor(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="simple project id"):
        module.compact_lessons_file(project)
    assert not (tmp_path / "data").exists()


def test_compactor_atomic_replace_preserves_original_when_publish_fails(tmp_path, monkeypatch):
    module = load_compactor(tmp_path, monkeypatch)
    target = tmp_path / "data" / "Memory" / "alpha" / "LESSONS.md"
    target.parent.mkdir(parents=True)
    target.write_text("old", encoding="utf-8")

    def fail_replace(source, destination):
        raise OSError("fixture replace failure")

    monkeypatch.setattr(module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="fixture replace failure"):
        module.atomic_write_text(target, "new")
    assert target.read_text(encoding="utf-8") == "old"
    assert not list(target.parent.glob("*.tmp"))


@pytest.mark.parametrize("application,expected", [
    ("openai", {"OPENAI_BASE_URL": "http://127.0.0.1:8787/v1", "OPENAI_API_BASE": "http://127.0.0.1:8787/v1"}),
    ("claude", {"ANTHROPIC_BASE_URL": "http://127.0.0.1:8787"}),
    ("auxiliary", {"OPENAI_BASE_URL": "http://127.0.0.1:8789/v1", "OPENAI_API_BASE": "http://127.0.0.1:8789/v1"}),
])
def test_application_launcher_changes_only_child_environment(tmp_path, application, expected):
    pwsh = shutil.which("pwsh")
    if not pwsh:
        pytest.skip("PowerShell 7 required")
    keys = ["OPENAI_BASE_URL", "OPENAI_API_BASE", "ANTHROPIC_BASE_URL", "DEVCORE_HEADROOM_ENFORCED"]
    # All values are fixtures; no secret or user environment is printed.
    fixture = tmp_path / "probe with spaces.py"
    fixture.write_text("import os,json,sys; print(json.dumps({'env': {k:os.environ.get(k) for k in " + repr(keys) + "}, 'args':sys.argv[1:]}))", encoding="utf-8")
    env = {**os.environ, **{key: "fixture-shared-value" for key in keys},
        "DEVCORE_LOCAL_ROOT": str(tmp_path / "local"), "DEVCORE_DATA_ROOT": str(tmp_path / "data"),
        "DEVCORE_PLATFORM_ROOT": str(tmp_path / "platform")}
    wrapper = tmp_path / "launch fixture.ps1"
    wrapper.write_text("param($Launcher,$Application,$Python,$Probe)\n& $Launcher -Application $Application -Command $Python -Arguments @($Probe, 'two words')\n", encoding="utf-8")
    command = subprocess.run([pwsh, "-NoProfile", "-File", str(wrapper), str(PLATFORM / "Scripts/init_agent_env.ps1"), application, sys.executable, str(fixture)],
        env=env, capture_output=True, text=True, timeout=15)
    assert command.returncode == 0, command.stderr
    result = json.loads(command.stdout)
    assert result["env"] == {key: expected.get(key) for key in keys}
    assert result["args"] == ["two words"]
    assert all(env[key] == "fixture-shared-value" for key in keys)
