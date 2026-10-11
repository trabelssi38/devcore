"""The automatic PowerShell scan must use local SQL, not shared task queues."""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


PLATFORM = Path(__file__).resolve().parents[1]


def _run(*args, cwd):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


def test_task_scan_uses_sql_and_preserves_shared_json(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _run("git", "init", "-q", cwd=repo)
    (repo / "note.txt").write_text("work", encoding="utf-8")
    _run("git", "add", "note.txt", cwd=repo)
    _run(
        "git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "commit", "-q", "-m", "[T-01] Completed in Git", cwd=repo,
    )

    shared = tmp_path / "shared"
    local = tmp_path / "local"
    config = tmp_path / "config"
    for folder in (shared, local, config):
        folder.mkdir()
    memory = shared / "Memory" / "alpha"
    memory.mkdir(parents=True)
    legacy = memory / "tasks.json"
    legacy.write_text(json.dumps({"project": "alpha", "tasks": [{"id": "T-99"}]}), encoding="utf-8")
    before = legacy.read_bytes()

    env = os.environ.copy()
    env.update({
        "DEVCORE_PLATFORM_ROOT": str(PLATFORM),
        "DEVCORE_CONFIG_ROOT": str(config),
        "DEVCORE_DATA_ROOT": str(shared),
        "DEVCORE_LOCAL_ROOT": str(local),
        "DEVCORE_PYTHON": sys.executable,
        "PYTHONPATH": str(PLATFORM),
    })
    command = [
        "powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
        "-File", str(PLATFORM / "Scripts" / "task_scan.ps1"),
        "-Project", "alpha", "-RepoPath", str(repo),
    ]
    for _ in range(2):
        result = subprocess.run(command, cwd=repo, env=env, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr

    with sqlite3.connect(local / "devcore.db") as conn:
        rows = conn.execute("SELECT id, project_id, status FROM tasks").fetchall()
    assert rows == [("T-01", "alpha", "done")]
    assert legacy.read_bytes() == before
    assert not list(shared.rglob("*queue.jsonl"))


def test_periodic_scan_is_disabled_and_project_is_required(tmp_path):
    jobs = json.loads((PLATFORM / "Scheduler" / "jobs.devcore.json").read_text(encoding="utf-8"))
    assert next(job for job in jobs if job["id"] == "periodic_task_scan")["enabled"] is False
    local = tmp_path / "local"
    shared = tmp_path / "shared"
    local.mkdir()
    shared.mkdir()
    env = os.environ.copy()
    env.update({
        "DEVCORE_LOCAL_ROOT": str(local),
        "DEVCORE_DATA_ROOT": str(shared),
    })
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(PLATFORM / "Scripts" / "task_scan.ps1")],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert not list(shared.iterdir())
    assert not list(local.iterdir())
