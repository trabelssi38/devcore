import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "DEV_CORE" / "Scripts" / "Auto" / "integrity_check.ps1"


def powershell():
    executable = shutil.which("powershell")
    if not executable:
        pytest.skip("Windows PowerShell is required for the legacy wrapper integration test")
    return executable


def _run(tmp_path, project=None, repo=None, data_root=None):
    args = [powershell(), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT)]
    if project is not None:
        args.extend(["-Project", project])
    if repo is not None:
        args.extend(["-RepoPath", str(repo)])
    env = os.environ.copy()
    env.update(
        DEVCORE_PLATFORM_ROOT=str(REPO_ROOT / "DEV_CORE"),
        DEVCORE_DATA_ROOT=str(data_root or tmp_path / "data"),
        DEVCORE_LOCAL_ROOT=str(tmp_path / "local"),
        DEVCORE_ACTIVE_PROJECT_NAME="beta",
    )
    return subprocess.run(args, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)


def _git_repo(path, message):
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--quiet", str(path)], check=True, timeout=20)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "DevCore fixture"], check=True, timeout=20)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "fixture@example.invalid"], check=True, timeout=20)
    (path / "fixture.txt").write_text("Temporary only.\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True, timeout=20)
    subprocess.run(["git", "-C", str(path), "commit", "--quiet", "-m", message], check=True, timeout=20)


def test_integrity_wrapper_requires_project_and_repo_before_data_access(tmp_path):
    repo = tmp_path / "repo"
    _git_repo(repo, "fixture")
    data_root = tmp_path / "data"
    missing = _run(tmp_path, repo=repo, data_root=data_root)
    traversal = _run(tmp_path, project="../beta", repo=repo, data_root=data_root)
    relative = _run(tmp_path, project="alpha", repo="repo", data_root=data_root)
    assert missing.returncode != 0
    assert traversal.returncode != 0
    assert relative.returncode != 0
    assert not data_root.exists()


def test_integrity_wrapper_reads_the_explicit_project_and_git_root(tmp_path):
    _git_repo(tmp_path, "[T-99] Decoy root must not leak")
    repo = tmp_path / "repo-alpha"
    _git_repo(repo, "[T-01] Alpha task")

    data_root = tmp_path / "data"
    for project, title in (("alpha", "Alpha task"), ("beta", "Beta task")):
        folder = data_root / "Memory" / project
        folder.mkdir(parents=True)
        (folder / "tasks.json").write_text(
            json.dumps({"tasks": [{"id": "T-01", "title": title, "status": "todo"}]}),
            encoding="utf-8",
        )

    result = _run(tmp_path, project="alpha", repo=repo, data_root=data_root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "T-99" not in result.stdout
    assert "Alpha task" not in result.stdout  # Healthy checks report no mismatches.
