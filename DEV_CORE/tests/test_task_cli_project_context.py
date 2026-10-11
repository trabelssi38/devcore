"""CLI task commands must not fall back to a machine-wide project."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from devcore_engine.services.tasks import TaskService


PLATFORM_ROOT = Path(__file__).resolve().parents[1]


def _env(tmp_path):
    env = os.environ.copy()
    env["DEVCORE_LOCAL_ROOT"] = str(tmp_path / "local")
    env["DEVCORE_DATA_ROOT"] = str(tmp_path / "shared")
    env["DEVCORE_PLATFORM_ROOT"] = str(PLATFORM_ROOT)
    env["DEVCORE_PYTHON"] = sys.executable
    env["PYTHONPATH"] = str(PLATFORM_ROOT)
    env["DEVCORE_ACTIVE_PROJECT_NAME"] = "wrong"
    return env


def _call(args, cwd, env):
    return subprocess.run(
        [sys.executable, "-m", "devcore_engine.cli", "task", *args],
        cwd=cwd, env=env, capture_output=True, text=True, check=False,
    )


@pytest.mark.parametrize("action", [["board"], ["next"], ["add", "unexpected"], ["complete", "T-01"]])
def test_task_cli_refuses_missing_project_before_opening_database(tmp_path, action):
    env = _env(tmp_path)
    result = _call(action, tmp_path, env)
    assert result.returncode == 2
    assert "task requires --project" in result.stderr
    assert not (tmp_path / "local" / "devcore.db").exists()


def test_task_cli_uses_local_manifest_for_mutations(tmp_path, monkeypatch):
    env = _env(tmp_path)
    for name in ("alpha", "beta"):
        manifest = tmp_path / name / ".devcore" / "project.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"name": name}), encoding="utf-8")
    (tmp_path / "alpha" / "nested").mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", env["DEVCORE_LOCAL_ROOT"])
    monkeypatch.setenv("DEVCORE_DATA_ROOT", env["DEVCORE_DATA_ROOT"])
    service = TaskService()
    service.add_task("alpha task", project_id="alpha")
    service.add_task("beta task", project_id="beta")
    service.conn.close()

    selected = _call(["next", "--json"], tmp_path / "alpha" / "nested", env)
    assert selected.returncode == 0, selected.stderr
    assert json.loads(selected.stdout)["project_id"] == "alpha"
    completed = _call(["complete", "T-01"], tmp_path / "alpha", env)
    assert completed.returncode == 0, completed.stderr
    created = _call(["add", "new beta task"], tmp_path / "beta", env)
    assert created.returncode == 0, created.stderr

    verify = TaskService()
    assert verify.get_task("T-01", "alpha")["status"] == "done"
    assert verify.get_task("T-01", "beta")["status"] == "todo"
    assert verify.get_task("T-02", "beta")["title"] == "new beta task"
    verify.conn.close()


def test_task_cli_reports_stale_step_and_completion(tmp_path, monkeypatch):
    env = _env(tmp_path)
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", env["DEVCORE_LOCAL_ROOT"])
    monkeypatch.setenv("DEVCORE_DATA_ROOT", env["DEVCORE_DATA_ROOT"])
    service = TaskService()
    task = service.add_task("versioned", steps=3, project_id="alpha")
    service.edit_task(task["id"], title="updated", project_id="alpha", expected_version=1)
    service.conn.close()

    for action in ("step", "complete"):
        stale = _call([action, task["id"], "--project", "alpha", "--expected-version", "1"], tmp_path, env)
        assert stale.returncode == 2
        assert "stale task version" in stale.stderr

    stepped = _call(["step", task["id"], "--project", "alpha", "--expected-version", "2"], tmp_path, env)
    assert stepped.returncode == 0, stepped.stderr
    completed = _call(["complete", task["id"], "--project", "alpha", "--expected-version", "3"], tmp_path, env)
    assert completed.returncode == 0, completed.stderr
    verify = TaskService()
    assert verify.get_task(task["id"], "alpha")["version"] == 4
    verify.conn.close()


def test_task_cli_reports_stale_status_transitions(tmp_path, monkeypatch):
    env = _env(tmp_path)
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", env["DEVCORE_LOCAL_ROOT"])
    monkeypatch.setenv("DEVCORE_DATA_ROOT", env["DEVCORE_DATA_ROOT"])
    service = TaskService()
    task = service.add_task("transition", project_id="alpha")
    active = service.next_task("alpha")
    current = service.edit_task(task["id"], title="revised", project_id="alpha",
                                expected_version=active["version"])
    service.conn.close()

    for action in ("pause", "skip"):
        stale = _call([action, task["id"], "--project", "alpha", "--expected-version",
                       str(active["version"])], tmp_path, env)
        assert stale.returncode == 2
        assert "stale task version" in stale.stderr

    for action, version in (("pause", current["version"]), ("resume", current["version"] + 1),
                            ("skip", current["version"] + 2)):
        result = _call([action, task["id"], "--project", "alpha", "--expected-version",
                        str(version)], tmp_path, env)
        assert result.returncode == 0, result.stderr
    verify = TaskService()
    assert verify.get_task(task["id"], "alpha")["status"] == "skipped"
    verify.conn.close()


def test_powershell_task_wrappers_use_manifest_when_project_is_omitted(tmp_path):
    env = _env(tmp_path)
    manifest = tmp_path / "alpha" / ".devcore" / "project.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"name": "alpha"}), encoding="utf-8")
    scripts = PLATFORM_ROOT / "Scripts"

    def wrapper(name, *args):
        return subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(scripts / name), *args],
            cwd=tmp_path / "alpha", env=env, capture_output=True, text=True, check=False,
        )

    added = wrapper("task_add.ps1", "-Title", "PowerShell task")
    assert added.returncode == 0, added.stderr
    assert "T-01" in added.stdout
    for script in ("task_status.ps1", "task_list.ps1"):
        listed = wrapper(script)
        assert listed.returncode == 0, listed.stderr
        assert "TASK BOARD (alpha)" in listed.stdout
