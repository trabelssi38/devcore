"""The installed PowerShell hook records through the service for its local manifest only."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess

import pytest

PLATFORM = Path(__file__).resolve().parents[1]
HOOKS = [PLATFORM / "Scripts/post_tool_hook.ps1", PLATFORM / "download/post_tool_hook.ps1"]
PYTHON = Path(r"E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe")


def _pwsh():
    executable = shutil.which("pwsh")
    if not executable:
        pytest.skip("PowerShell 7 is required")
    if not PYTHON.is_file():
        pytest.skip("Documented Python 3.13 runtime is unavailable")
    return executable


def _env(tmp_path):
    env = dict(os.environ)
    env.update({
        "DEVCORE_PLATFORM_ROOT": str(PLATFORM),
        "DEVCORE_LOCAL_ROOT": str(tmp_path / "local"),
        "DEVCORE_DATA_ROOT": str(tmp_path / "data"),
        "DEVCORE_PYTHON": str(PYTHON),
        "DEVCORE_ACTIVE_PROJECT_NAME": "beta",
    })
    return env


def _manifest(root: Path, project: str):
    manifest = root / ".devcore/project.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"name": project}), encoding="utf-8")
    return manifest


def _run(root: Path, env, hook):
    return subprocess.run(
        [_pwsh(), "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(hook)],
        cwd=root, env=env, capture_output=True, text=True, timeout=30,
    )


@pytest.mark.parametrize("hook", HOOKS)
def test_hook_uses_each_cwd_manifest_and_never_touches_legacy_task_json(tmp_path, hook):
    env = _env(tmp_path)
    alpha, beta = tmp_path / "alpha", tmp_path / "beta"
    alpha.mkdir(); beta.mkdir()
    _manifest(alpha, "alpha")
    _manifest(beta, "beta")
    legacy = tmp_path / "data/Memory/beta/tasks.json"
    legacy.parent.mkdir(parents=True)
    legacy_content = '{"project":"beta","tasks":[]}\n'
    legacy.write_text(legacy_content, encoding="utf-8")

    for root in (alpha, beta):
        result = _run(root, env, hook)
        assert result.returncode == 0, result.stderr + result.stdout

    conn = sqlite3.connect(tmp_path / "local/devcore.db")
    try:
        metrics = conn.execute("SELECT project, count(*) FROM metrics WHERE source='post_tool_hook' GROUP BY project ORDER BY project").fetchall()
        events = conn.execute("SELECT project, event_type FROM bus_events WHERE event_type='ToolExecuted' ORDER BY project").fetchall()
    finally:
        conn.close()
    assert metrics == [("alpha", 1), ("beta", 1)]
    assert events == [("alpha", "ToolExecuted"), ("beta", "ToolExecuted")]
    assert legacy.read_text(encoding="utf-8") == legacy_content
    assert not (tmp_path / "data/Memory/LESSONS.md").exists()


@pytest.mark.parametrize("hook", HOOKS)
def test_hook_without_local_manifest_ignores_machine_active_project(tmp_path, hook):
    env = _env(tmp_path)
    unregistered = tmp_path / "unregistered"
    unregistered.mkdir()
    result = _run(unregistered, env, hook)
    assert result.returncode == 0, result.stderr + result.stdout
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "local").exists()
