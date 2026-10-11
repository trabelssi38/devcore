import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "DEV_CORE" / "Scripts" / "Auto" / "task_git_scanner.ps1"


def powershell():
    executable = shutil.which("powershell")
    if not executable:
        pytest.skip("Windows PowerShell is required for the legacy scanner integration test")
    return executable


def _run(tmp_path, data_root, repo=None, project=None):
    args = [powershell(), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT)]
    if project is not None:
        args.extend(["-Project", project])
    if repo is not None:
        args.extend(["-RepoPath", str(repo)])
    env = os.environ.copy()
    env.update(
        DEVCORE_PLATFORM_ROOT=str(REPO_ROOT / "DEV_CORE"),
        DEVCORE_DATA_ROOT=str(data_root),
        DEVCORE_LOCAL_ROOT=str(tmp_path / "local"),
        DEVCORE_ACTIVE_PROJECT_NAME="beta",
    )
    return subprocess.run(args, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)


def test_git_scanner_requires_project_repo_and_explicit_data_root(tmp_path):
    data_root = tmp_path / "data"
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True, timeout=20)
    missing_project = _run(tmp_path, data_root, repo=repo)
    missing_repo = _run(tmp_path, data_root, project="alpha")
    traversal = _run(tmp_path, data_root, repo=repo, project="../beta")
    env = os.environ.copy()
    env.pop("DEVCORE_DATA_ROOT", None)
    env.update(DEVCORE_PLATFORM_ROOT=str(REPO_ROOT / "DEV_CORE"))
    no_data_root = subprocess.run(
        [powershell(), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT),
         "-Project", "alpha", "-RepoPath", str(repo)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
    )
    assert missing_project.returncode != 0
    assert missing_repo.returncode != 0
    assert traversal.returncode != 0
    assert no_data_root.returncode != 0
    assert not data_root.exists()


def test_git_scanner_updates_only_the_explicit_project_and_repo(tmp_path):
    repo = tmp_path / "repo-alpha"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True, timeout=20)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "DevCore fixture"], check=True, timeout=20)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "fixture@example.invalid"], check=True, timeout=20)
    (repo / "README.md").write_text("Temporary fixture.\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, timeout=20)
    subprocess.run(["git", "-C", str(repo), "commit", "--quiet", "-m", "[T-01] Alpha task"], check=True, timeout=20)

    data_root = tmp_path / "data"
    for project, title in (("alpha", "Alpha task"), ("beta", "Beta task")):
        folder = data_root / "Memory" / project
        folder.mkdir(parents=True)
        (folder / "tasks.json").write_text(
            json.dumps({"project": project, "current_task": None, "tasks": [{"id": "T-01", "title": title, "status": "todo"}]}),
            encoding="utf-8",
        )
    beta_path = data_root / "Memory" / "beta" / "tasks.json"
    beta_before = beta_path.read_bytes()

    result = _run(tmp_path, data_root, repo=repo, project="alpha")
    assert result.returncode == 0, result.stdout + result.stderr
    alpha = json.loads((data_root / "Memory" / "alpha" / "tasks.json").read_text(encoding="utf-8-sig"))
    assert alpha["detected_from_git"] == ["T-01"]
    assert alpha["tasks"][0]["commit_hash"]
    assert beta_path.read_bytes() == beta_before
    assert (data_root / "Logs" / "scripts" / "alpha").is_dir()
    assert not (data_root / "Logs" / "scripts" / "beta").exists()
    assert (data_root / "Memory" / "alpha" / "task_git_queue.jsonl").exists() is False
