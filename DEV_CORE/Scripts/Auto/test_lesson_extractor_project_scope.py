"""PowerShell lesson extraction stays inside one registered project and temp store."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

PLATFORM = Path(__file__).resolve().parents[2]
LESSON_EXTRACTOR = PLATFORM / "Scripts/Auto/lesson_extractor.ps1"
PYTHON = Path(r"E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe")


def pwsh():
    executable = shutil.which("pwsh")
    if not executable:
        pytest.skip("PowerShell 7 is required")
    if not PYTHON.is_file():
        pytest.skip("Documented Python 3.13 runtime is unavailable")
    return executable


def make_repo(path: Path, subject: str):
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "fixture@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Fixture"], check=True)
    (path / "fixture.txt").write_text(subject, encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "fixture.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", subject], check=True)


def make_env(tmp_path: Path, alpha: Path, beta: Path):
    config = tmp_path / "config"
    config.mkdir()
    (config / "projects.json").write_text(json.dumps({"projects": [
        {"name": "alpha", "path": str(alpha)}, {"name": "beta", "path": str(beta)},
    ]}), encoding="utf-8")
    data = tmp_path / "data"
    env = {
        **os.environ,
        "DEVCORE_PLATFORM_ROOT": str(PLATFORM),
        "DEVCORE_CONFIG_ROOT": str(config),
        "DEVCORE_LOCAL_ROOT": str(tmp_path / "local"),
        "DEVCORE_DATA_ROOT": str(data),
        "DEVCORE_PYTHON": str(PYTHON),
        "DEVCORE_ACTIVE_PROJECT_NAME": "beta",
    }
    return env, data


def seed_done_tasks(tmp_path: Path, env):
    script = tmp_path / "seed.py"
    script.write_text(
        "from devcore_engine.services.tasks import TaskService\n"
        "s=TaskService()\n"
        "a=s.add_task('Alpha fixture lesson', project_id='alpha')\n"
        "b=s.add_task('Beta secret lesson', project_id='beta')\n"
        "s.complete_task(a['id'], 'alpha')\n"
        "s.complete_task(b['id'], 'beta')\n"
        "s.conn.close()\n",
        encoding="utf-8",
    )
    subprocess.run([str(PYTHON), str(script)], cwd=PLATFORM, env=env, check=True, capture_output=True, text=True)


def run_extractor(env, project="alpha"):
    args = [] if project is None else ["-Project", project]
    return subprocess.run(
        [pwsh(), "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(LESSON_EXTRACTOR), *args],
        cwd=PLATFORM, env=env, capture_output=True, text=True, timeout=45,
    )


def test_extractor_reads_transactional_project_board_and_writes_only_scoped_outputs(tmp_path):
    alpha, beta = tmp_path / "repos/alpha", tmp_path / "repos/beta"
    make_repo(alpha, "feat: alpha change")
    make_repo(beta, "fix: beta secret change")
    env, data = make_env(tmp_path, alpha, beta)
    seed_done_tasks(tmp_path, env)
    shared_legacy = data / "Memory/LESSONS.md"
    shared_legacy.parent.mkdir(parents=True)
    shared_text = "legacy shared lessons remain unchanged\n"
    shared_legacy.write_text(shared_text, encoding="utf-8")
    beta_memory = data / "Memory/beta/LESSONS.md"
    beta_memory.parent.mkdir(parents=True)
    beta_text = "# Beta private lesson\n"
    beta_memory.write_text(beta_text, encoding="utf-8")

    result = run_extractor(env)
    assert result.returncode == 0, result.stderr + result.stdout
    alpha_text = (data / "Memory/alpha/LESSONS.md").read_text(encoding="utf-8")
    assert "alpha fixture lesson" in alpha_text
    assert "1 feat, 0 fix" in alpha_text
    assert "beta secret" not in alpha_text and "beta change" not in alpha_text
    assert shared_legacy.read_text(encoding="utf-8") == shared_text
    assert beta_memory.read_text(encoding="utf-8") == beta_text
    note = next((data / "Vault/Lessons/alpha/workflow").glob("session_*.md")).read_text(encoding="utf-8")
    assert "project: alpha" in note and "alpha fixture lesson" in note
    assert "beta secret" not in note
    assert list((data / "Logs/scripts/alpha").glob("lesson_extractor_*.log"))
    assert not (data / "Logs/scripts/beta").exists()
    assert not (data / "Vault/Lessons/workflow").exists()

    # Existing target replacement and repeated invocation are safe and idempotent.
    assert run_extractor(env).returncode == 0
    alpha_text_after = (data / "Memory/alpha/LESSONS.md").read_text(encoding="utf-8")
    assert alpha_text_after.count("lesson:T-01") == 1
    assert shared_legacy.read_text(encoding="utf-8") == shared_text
    assert beta_memory.read_text(encoding="utf-8") == beta_text


def test_legacy_call_without_project_exits_successfully_without_touching_data(tmp_path):
    alpha, beta = tmp_path / "repos/alpha", tmp_path / "repos/beta"
    make_repo(alpha, "feat: alpha")
    make_repo(beta, "fix: beta")
    env, data = make_env(tmp_path, alpha, beta)
    result = run_extractor(env, project=None)
    assert result.returncode == 0
    assert "explicit -Project" in result.stdout + result.stderr
    assert not data.exists()


@pytest.mark.parametrize("project", ["../beta", "alpha/beta", "C:beta"])
def test_extractor_rejects_path_like_project_before_touching_data(tmp_path, project):
    alpha, beta = tmp_path / "repos/alpha", tmp_path / "repos/beta"
    make_repo(alpha, "feat: alpha")
    make_repo(beta, "fix: beta")
    env, data = make_env(tmp_path, alpha, beta)
    result = run_extractor(env, project)
    assert result.returncode != 0
    assert not data.exists()


def test_extractor_refuses_unregistered_or_non_root_repo_before_data_access(tmp_path):
    alpha, beta = tmp_path / "repos/alpha", tmp_path / "repos/beta"
    make_repo(alpha, "feat: alpha")
    make_repo(beta, "fix: beta")
    env, data = make_env(tmp_path, alpha / "nested", beta)
    (alpha / "nested").mkdir()
    result = run_extractor(env)
    assert result.returncode != 0
    assert not data.exists()
