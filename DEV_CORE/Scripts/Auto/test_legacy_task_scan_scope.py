from datetime import datetime
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
AUTO = REPO_ROOT / "DEV_CORE" / "Scripts" / "Auto"


def powershell():
    executable = shutil.which("powershell")
    if not executable:
        pytest.skip("Windows PowerShell is required for the legacy wrapper integration test")
    return executable


def test_platform_version_preserves_new_explicit_data_root(tmp_path):
    powershell_exe = powershell()
    explicit_root = tmp_path / "not-created-yet"
    bootstrap = tmp_path / "check-explicit-root.ps1"
    bootstrap.write_text(
        f"$env:DEVCORE_DATA_ROOT = '{explicit_root}'\n"
        f"$env:DEVCORE_PLATFORM_ROOT = '{REPO_ROOT / 'DEV_CORE'}'\n"
        f". '{REPO_ROOT / 'DEV_CORE' / 'Scripts' / 'platform_version.ps1'}'\n"
        "Write-Output ('ROOT=' + $env:DEVCORE_DATA_ROOT)\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [powershell_exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(bootstrap)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"ROOT={explicit_root}" in result.stdout
    assert not explicit_root.exists()


def test_spec_parser_requires_project_and_ignores_active_project_guess(tmp_path):
    powershell_exe = powershell()
    data_root = tmp_path / "data"
    local_root = tmp_path / "local"
    repo = tmp_path / "source"
    specs = repo / "docs" / "superpowers" / "specs"
    specs.mkdir(parents=True)
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True, timeout=20)
    (specs / "feature.md").write_text("# Feature\n\n- [ ] Add scoped parser\n", encoding="utf-8")
    env = os.environ.copy()
    env.update(
        DEVCORE_PLATFORM_ROOT=str(REPO_ROOT / "DEV_CORE"),
        DEVCORE_DATA_ROOT=str(data_root),
        DEVCORE_LOCAL_ROOT=str(local_root),
        DEVCORE_ACTIVE_PROJECT_NAME="beta",
    )
    script = AUTO / "task_spec_parser.ps1"

    missing = subprocess.run(
        [powershell_exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script)],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert missing.returncode != 0
    assert not data_root.exists()

    completed = subprocess.run(
        [powershell_exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Project", "alpha"],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    alpha_queue = data_root / "Memory" / "alpha" / "task_spec_queue.jsonl"
    assert alpha_queue.exists(), completed.stdout + completed.stderr
    assert "Add scoped parser" in alpha_queue.read_text(encoding="utf-8")
    assert not (data_root / "Memory" / "beta").exists()


def test_prompt_analyzer_powershell_wrapper_forwards_project(tmp_path):
    powershell_exe = powershell()
    data_root = tmp_path / "data"
    env = os.environ.copy()
    env.update(
        DEVCORE_PLATFORM_ROOT=str(REPO_ROOT / "DEV_CORE"),
        DEVCORE_DATA_ROOT=str(data_root),
        DEVCORE_LOCAL_ROOT=str(tmp_path / "local"),
        DEVCORE_PYTHON=sys.executable,
        DEVCORE_ACTIVE_PROJECT_NAME="beta",
        ANTIGRAVITY_BRAIN_DIR=str(tmp_path / "no-brain-fixture"),
        PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""),
    )
    script = AUTO / "task_prompt_analyzer.ps1"
    completed = subprocess.run(
        [powershell_exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Project", "alpha"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    today = datetime.now().strftime("%Y-%m-%d")
    analyzer_log = data_root / "Logs" / "scripts" / f"task_prompt_analyzer_{today}.log"
    assert analyzer_log.exists(), completed.stdout + completed.stderr
    assert "project: 'alpha'" in analyzer_log.read_text(encoding="utf-8")
    assert not (data_root / "Memory" / "beta").exists()


def test_task_scan_routes_git_and_legacy_suggestions_to_explicit_project(tmp_path):
    powershell_exe = powershell()
    repo = tmp_path / "source"
    specs = repo / "docs" / "superpowers" / "specs"
    specs.mkdir(parents=True)
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True, timeout=20)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "DevCore fixture"], check=True, timeout=20)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "fixture@example.invalid"], check=True, timeout=20)
    (repo / "README.md").write_text("Temporary fixture only.\n", encoding="utf-8")
    (specs / "feature.md").write_text("# Feature\n\n- [ ] Add scoped parser\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, timeout=20)
    subprocess.run(["git", "-C", str(repo), "commit", "--quiet", "-m", "Add temporary fixture"], check=True, timeout=20)

    data_root = tmp_path / "data"
    local_root = tmp_path / "local"
    env = os.environ.copy()
    env.update(
        DEVCORE_PLATFORM_ROOT=str(REPO_ROOT / "DEV_CORE"),
        DEVCORE_DATA_ROOT=str(data_root),
        DEVCORE_LOCAL_ROOT=str(local_root),
        DEVCORE_PYTHON=sys.executable,
        DEVCORE_ACTIVE_PROJECT_NAME="beta",
        ANTIGRAVITY_BRAIN_DIR=str(tmp_path / "no-brain-fixture"),
    )
    script = REPO_ROOT / "DEV_CORE" / "Scripts" / "task_scan.ps1"
    completed = subprocess.run(
        [powershell_exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script),
         "-Project", "alpha", "-RepoPath", str(repo), "-IncludeLegacySuggestions"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    spec_queue = data_root / "Memory" / "alpha" / "task_spec_queue.jsonl"
    assert spec_queue.exists(), completed.stdout + completed.stderr
    assert "Add scoped parser" in spec_queue.read_text(encoding="utf-8")
    assert not (data_root / "Memory" / "beta").exists()
    conn = sqlite3.connect(local_root / "devcore.db")
    try:
        assert conn.execute("SELECT COUNT(*) FROM tasks WHERE project_id='alpha'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM tasks WHERE project_id='beta'").fetchone()[0] == 0
    finally:
        conn.close()
