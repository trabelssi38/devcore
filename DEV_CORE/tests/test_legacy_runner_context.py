"""Legacy automatic entry points must keep project identity and truthful receipts."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest

from devcore_engine.services.tasks import TaskService

PLATFORM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLATFORM / "Tools"))
from devcore.agent_runner import CodexManualAgentRunner


def test_manual_instructions_are_separated_by_project_and_attempt(tmp_path):
    runner = CodexManualAgentRunner(tmp_path / "shared", session_root=tmp_path / "local" / "Sessions")
    receipts = [runner.run({"id": "T-01", "project_id": project, "title": project})
                for project in ("alpha", "beta", "alpha")]
    files = [Path(receipt["prompt_path"]) for receipt in receipts]
    assert len(set(files)) == 3
    for project, file in zip(("alpha", "beta", "alpha"), files):
        assert file.is_relative_to(tmp_path / "local" / "Sessions" / project / "T-01")
        assert f"Project: {project}" in file.read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        runner.run({"id": "../escape", "project_id": "alpha"})
    with pytest.raises(ValueError):
        runner.run({"id": "T-01"})
    assert not (tmp_path / "shared").exists()


def test_automatic_task_check_uses_explicit_sqlite_project(tmp_path, monkeypatch):
    local, shared = tmp_path / "local", tmp_path / "shared"
    local.mkdir()
    shared.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared))
    monkeypatch.setenv("DEVCORE_ACTIVE_PROJECT_NAME", "beta")
    service = TaskService()
    for project in ("alpha", "beta"):
        service.add_task(project, project_id=project)
        service.next_task(project)
    service.conn.close()

    spec = importlib.util.spec_from_file_location("isolated_check_active_task", PLATFORM / "Scripts" / "Auto" / "check_active_task.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    received = []

    class Runner:
        def report_status(self):
            return {"status": "OK"}

        def run(self, task):
            received.append(task)
            return {"status": "manual", "executed": False}

    monkeypatch.setattr(module, "get_agent_runner", lambda: Runner())
    assert module.main(["--project", "alpha"]) == 0
    assert received[0]["project_id"] == "alpha"
    assert received[0]["id"] == "T-01"
    assert not list(shared.rglob("tasks.json"))


def test_automatic_task_check_refuses_missing_context_before_opening_database(tmp_path):
    env = os.environ.copy()
    env.update(DEVCORE_LOCAL_ROOT=str(tmp_path / "local"), DEVCORE_DATA_ROOT=str(tmp_path / "shared"),
               DEVCORE_ACTIVE_PROJECT_NAME="wrong", PYTHONPATH=str(PLATFORM))
    result = subprocess.run([sys.executable, str(PLATFORM / "Scripts" / "Auto" / "check_active_task.py")],
                            cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 2
    assert "--project or a local" in result.stderr
    assert not (tmp_path / "local").exists()
    assert not (tmp_path / "shared").exists()


def test_workflow_does_not_complete_a_manual_agent_step(tmp_path, monkeypatch):
    from devcore import orchestrator

    local, shared = tmp_path / "local", tmp_path / "shared"
    local.mkdir()
    shared.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared))
    state = orchestrator.WorkflowPlanner.plan_workflow("""
name: Manual action
project: alpha
steps:
  - id: step-1
    task: implement
""")
    monkeypatch.setattr(orchestrator, "get_agent_runner", lambda: CodexManualAgentRunner(shared, local / "Sessions"))
    executor = orchestrator.WorkflowExecutor(state)
    executor.execute_all()
    assert state.status == "failed"
    assert state.steps["step-1"]["status"] == "failed"
    assert "manual" in state.steps["step-1"]["error_message"]
    assert len(list((local / "Sessions" / "alpha").rglob("manual-instruction.md"))) == 1
