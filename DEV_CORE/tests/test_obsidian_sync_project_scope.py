"""Daily notes derive from the transactional board and stay within one project."""

import os
from pathlib import Path
import subprocess
import sys

from devcore_engine.services.tasks import TaskService


PLATFORM = Path(__file__).resolve().parents[1]


def _run(script: str, env: dict[str, str]):
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(PLATFORM / script), "-Project", env["TEST_PROJECT"]],
        env=env, cwd=PLATFORM, capture_output=True, text=True, timeout=30,
    )


def test_obsidian_sync_is_scoped_to_project_and_idempotent(tmp_path, monkeypatch):
    local_root, data_root = tmp_path / "local", tmp_path / "data"
    local_root.mkdir()
    data_root.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(data_root))

    service = TaskService()
    try:
        for project in ("alpha", "beta"):
            service.add_task(f"{project} completed", project_id=project)
            service.next_task(project)
            service.complete_task("T-01", project_id=project)
    finally:
        service.conn.close()

    today = __import__("datetime").date.today().isoformat()
    legacy = data_root / "Vault" / "Daily Notes" / f"{today}.md"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("GLOBAL ORIGINAL\n", encoding="utf-8")

    env = os.environ.copy()
    env.update({
        "DEVCORE_PLATFORM_ROOT": str(PLATFORM),
        "DEVCORE_PYTHON": sys.executable,
        "DEVCORE_ACTIVE_PROJECT_NAME": "beta",
    })
    env["TEST_PROJECT"] = "alpha"
    for _ in range(2):
        result = _run("Scripts/obsidian_sync.ps1", env)
        assert result.returncode == 0, result.stderr + result.stdout
    env["TEST_PROJECT"] = "beta"
    result = _run("Scripts/Auto/obsidian_sync.ps1", env)
    assert result.returncode == 0, result.stderr + result.stdout

    alpha = (data_root / "Vault" / "Daily Notes" / "alpha" / f"{today}.md").read_text(encoding="utf-8")
    beta = (data_root / "Vault" / "Daily Notes" / "beta" / f"{today}.md").read_text(encoding="utf-8")
    assert alpha.count("**T-01**: alpha completed") == 1
    assert "beta completed" not in alpha
    assert "**T-01**: beta completed" in beta
    assert "alpha completed" not in beta
    assert legacy.read_text(encoding="utf-8") == "GLOBAL ORIGINAL\n"
    assert not list(data_root.rglob("tasks.json"))


def test_obsidian_sync_requires_project_before_writing(tmp_path):
    data_root = tmp_path / "data"
    env = os.environ.copy()
    env.update({
        "DEVCORE_DATA_ROOT": str(data_root),
        "DEVCORE_LOCAL_ROOT": str(tmp_path / "local"),
        "DEVCORE_PLATFORM_ROOT": str(PLATFORM),
        "DEVCORE_PYTHON": sys.executable,
    })
    for script in ("Scripts/obsidian_sync.ps1", "Scripts/Auto/obsidian_sync.ps1"):
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(PLATFORM / script)],
            env=env, cwd=PLATFORM, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode != 0
    assert not data_root.exists()
