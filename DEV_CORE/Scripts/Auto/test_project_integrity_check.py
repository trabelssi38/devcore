import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "DEV_CORE" / "Scripts" / "Auto" / "integrity_check.py"


def _run(tmp_path, project=None, repo=None):
    env = os.environ.copy()
    env.update(
        DEVCORE_PLATFORM_ROOT=str(REPO_ROOT / "DEV_CORE"),
        DEVCORE_DATA_ROOT=str(tmp_path / "data"),
        DEVCORE_ACTIVE_PROJECT_NAME="beta",
    )
    args = [sys.executable, str(SCRIPT)]
    if project is not None:
        args.extend(["--project", project])
    if repo is not None:
        args.extend(["--repo", str(repo)])
    return subprocess.run(args, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)


def test_integrity_check_requires_explicit_safe_project_and_repo(tmp_path):
    missing = _run(tmp_path)
    traversal = _run(tmp_path, "../beta", tmp_path)
    relative_repo = _run(tmp_path, "alpha", Path("."))
    assert missing.returncode != 0
    assert traversal.returncode != 0
    assert relative_repo.returncode != 0
    assert not (tmp_path / "data").exists()


def test_integrity_check_reads_only_the_requested_project_and_repo(tmp_path):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True, timeout=20)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Decoy fixture"], check=True, timeout=20)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "decoy@example.invalid"], check=True, timeout=20)
    (tmp_path / "decoy.txt").write_text("wrong repo", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "decoy.txt"], check=True, timeout=20)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "--quiet", "-m", "[T-99] Must not leak into alpha"], check=True, timeout=20)

    repo = tmp_path / "repo-alpha"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True, timeout=20)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "DevCore fixture"], check=True, timeout=20)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "fixture@example.invalid"], check=True, timeout=20)
    (repo / "README.md").write_text("Temporary fixture.\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, timeout=20)
    subprocess.run(["git", "-C", str(repo), "commit", "--quiet", "-m", "fixture"], check=True, timeout=20)

    data = tmp_path / "data" / "Memory"
    alpha = data / "alpha"
    beta = data / "beta"
    alpha.mkdir(parents=True)
    beta.mkdir(parents=True)
    (alpha / "tasks.json").write_text(json.dumps({"tasks": [{"id": "A-1", "title": "Alpha", "status": "todo"}]}), encoding="utf-8")
    (beta / "tasks.json").write_text(json.dumps({"tasks": [{"id": "B-1", "title": "", "status": "done"}]}), encoding="utf-8")

    result = _run(tmp_path, "alpha", repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "T-99" not in result.stdout
    assert "problème(s)" not in result.stdout
    assert not list(data.rglob("*.jsonl"))

    foreign = _run(tmp_path, "beta", repo)
    assert foreign.returncode == 1
    assert "B-1" in foreign.stdout
    assert "A-1" not in foreign.stdout
