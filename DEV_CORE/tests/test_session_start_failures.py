"""The session hook must not leave a successful daily flag after failure."""

import os
import subprocess
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "Scripts" / "session_start.ps1"


def _fixture(tmp_path, project_output, launch_script):
    platform = tmp_path / "platform"
    scripts = platform / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "session_start.ps1").write_bytes(SOURCE.read_bytes())
    (scripts / "platform_version.ps1").write_text("# isolated", encoding="utf-8")
    (scripts / "Get-ActiveProject.ps1").write_text(
        f'Write-Output "{project_output}"\n', encoding="utf-8",
    )
    (scripts / "launch.ps1").write_text(launch_script, encoding="utf-8")
    project = tmp_path / "project"
    manifest = project / ".devcore"
    manifest.mkdir(parents=True)
    (manifest / "project.json").write_text('{"name":"alpha"}', encoding="utf-8")
    local = tmp_path / "local"
    data = tmp_path / "data"
    env = os.environ.copy()
    env.update({"DEVCORE_PLATFORM_ROOT": str(platform),
                "DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data)})
    return scripts, project, local, data, env


def _run(scripts, project, env, *args):
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
         "Bypass", "-File", str(scripts / "session_start.ps1"), *args],
        cwd=project, env=env, capture_output=True, text=True, timeout=30,
    )


def _assert_no_success_log(local):
    for log in local.rglob("session_start_*.log"):
        assert "session_start.ps1 termine" not in log.read_text(encoding="utf-8-sig")


def test_session_start_rejects_invalid_project_before_writing(tmp_path):
    scripts, project, local, data, env = _fixture(tmp_path, "../beta", "exit 0\n")
    result = _run(scripts, project, env)
    assert result.returncode != 0
    assert not local.exists()
    assert not data.exists()


def test_session_start_clears_daily_flag_after_launch_failure(tmp_path):
    scripts, project, local, data, env = _fixture(tmp_path, "alpha", "exit 7\n")
    result = _run(scripts, project, env)
    assert result.returncode != 0
    assert "Lancement de session echoue" in result.stderr
    assert not list(local.rglob("*.flag"))
    _assert_no_success_log(local)
    assert not data.exists()


@pytest.mark.parametrize("failed_step", ["task_add", "task_next", "gen_session_context"])
def test_session_start_clears_flag_after_task_or_context_failure(tmp_path, failed_step):
    scripts, project, local, data, env = _fixture(tmp_path, "alpha", "exit 0\n")
    fake_python = scripts / "fake_python.ps1"
    tasks = [] if failed_step == "task_add" else [{"id": "T-01", "status": "todo"}]
    import json
    board = json.dumps({"project": "alpha", "tasks": tasks})
    fake_python.write_text(f"Write-Output '{board}'\nexit 0\n", encoding="utf-8")
    (scripts / "platform_version.ps1").write_text(
        f"function Get-DevCorePython {{ return '{fake_python}' }}\n",
        encoding="utf-8",
    )
    for name in ("task_add", "task_next", "gen_session_context"):
        code = 7 if name == failed_step else 0
        (scripts / f"{name}.ps1").write_text(f"exit {code}\n", encoding="utf-8")
    result = _run(scripts, project, env)
    assert result.returncode != 0, result.stdout + result.stderr
    assert not list(local.rglob("*.flag"))
    _assert_no_success_log(local)
    assert not data.exists()


def test_session_start_clears_flag_after_optional_maintenance_failure(tmp_path):
    scripts, project, local, data, env = _fixture(tmp_path, "alpha", "exit 0\n")
    fake_python = scripts / "fake_python.ps1"
    fake_python.write_text(
        "Write-Output '{\"project\":\"alpha\",\"tasks\":[{\"id\":\"T-01\",\"status\":\"todo\"}]}'\nexit 0\n",
        encoding="utf-8",
    )
    (scripts / "platform_version.ps1").write_text(
        f"function Get-DevCorePython {{ return '{fake_python}' }}\n",
        encoding="utf-8",
    )
    (scripts / "task_next.ps1").write_text("exit 0\n", encoding="utf-8")
    (scripts / "endday_check.ps1").write_text("exit 7\n", encoding="utf-8")
    result = _run(scripts, project, env, "-RunLegacyGlobalMaintenance")
    assert result.returncode != 0, result.stdout + result.stderr
    assert not list(local.rglob("*.flag"))
    _assert_no_success_log(local)
    assert not data.exists()


def test_session_start_rejects_foreign_board_before_task_selection(tmp_path):
    scripts, project, local, data, env = _fixture(tmp_path, "alpha", "exit 0\n")
    fake_python = scripts / "fake_python.ps1"
    fake_python.write_text(
        "Write-Output '{\"project\":\"beta\",\"tasks\":[{\"id\":\"T-01\",\"status\":\"todo\"}]}'\nexit 0\n",
        encoding="utf-8",
    )
    (scripts / "platform_version.ps1").write_text(
        f"function Get-DevCorePython {{ return '{fake_python}' }}\n",
        encoding="utf-8",
    )
    (scripts / "task_next.ps1").write_text(
        'Set-Content $env:DCC_TASK_CALLED "yes"\nexit 0\n', encoding="utf-8",
    )
    marker = tmp_path / "task_called.txt"
    env["DCC_TASK_CALLED"] = str(marker)
    result = _run(scripts, project, env)
    assert result.returncode != 0
    assert "Board du mauvais projet" in result.stderr
    assert not marker.exists()
    assert not list(local.rglob("*.flag"))
    _assert_no_success_log(local)
    assert not data.exists()
