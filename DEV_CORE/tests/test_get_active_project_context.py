"""PowerShell project detection must not read or write a global selection."""

import json
import os
import subprocess
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "Scripts" / "Get-ActiveProject.ps1"


def _detect(cwd, env, *args):
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(SCRIPT), *args],
        cwd=cwd, env=env, capture_output=True, text=True, check=False,
        encoding="utf-8", errors="replace",
    )


def test_detects_each_manifest_without_changing_global_file(tmp_path):
    local = tmp_path / "local"
    runtime = local / "Runtime"
    runtime.mkdir(parents=True)
    active_file = runtime / "active_project.txt"
    active_file.write_text("wrong", encoding="utf-8")
    env = os.environ.copy()
    env["DEVCORE_LOCAL_ROOT"] = str(local)
    env["DEVCORE_DATA_ROOT"] = str(tmp_path / "shared")
    env["DEVCORE_ACTIVE_PROJECT_NAME"] = "wrong"

    for name in ("alpha", "beta"):
        root = tmp_path / name
        manifest = root / ".devcore" / "project.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"name": name}), encoding="utf-8")
        (root / "nested").mkdir()
        result = _detect(root / "nested", env)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == name
    assert active_file.read_text(encoding="utf-8") == "wrong"


@pytest.mark.parametrize("marker", ["none", "git_directory", "worktree_file"])
def test_unregistered_directory_never_uses_previous_project(tmp_path, marker):
    root = tmp_path / "newrepo"
    root.mkdir()
    if marker == "git_directory":
        (root / ".git").mkdir()
    elif marker == "worktree_file":
        (root / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
    env = os.environ.copy()
    env["DEVCORE_ACTIVE_PROJECT_NAME"] = "wrong"
    result = _detect(root, env)
    if marker == "git_directory":
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "newrepo"
    else:
        assert result.returncode != 0
        assert "wrong" not in result.stdout


def test_explicit_project_is_validated(tmp_path):
    good = _detect(tmp_path, os.environ.copy(), "-Project", "alpha")
    assert good.returncode == 0
    assert good.stdout.strip() == "alpha"
    bad = _detect(tmp_path, os.environ.copy(), "-Project", "../other")
    assert bad.returncode != 0


def test_session_start_aborts_before_initialization_without_project(tmp_path):
    env = os.environ.copy()
    env["DEVCORE_PLATFORM_ROOT"] = str(SCRIPT.parent.parent)
    env["DEVCORE_LOCAL_ROOT"] = str(tmp_path / "local")
    env["DEVCORE_DATA_ROOT"] = str(tmp_path / "shared")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(SCRIPT.parent / "session_start.ps1")],
        cwd=tmp_path, env=env, capture_output=True, text=True, check=False,
        encoding="utf-8", errors="replace",
    )
    assert result.returncode != 0
    assert not (tmp_path / "local" / "devcore.db").exists()
    assert not (tmp_path / "shared" / "Memory").exists()
