import sys
import pytest
from pathlib import Path

# Ensure devcore is in path
tools_dir = Path(__file__).resolve().parent.parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from devcore.state_engine import StateEngine
from devcore.orchestrator import WorkflowPlanner, WorkflowExecutor


def test_workflow_resumption_skips_succeeded(tmp_path):
    """Verify that a resumed workflow does not re-execute steps that already succeeded."""
    yaml_wf = """
name: "Resumption Test"
steps:
  - id: step-1
    command: python -c "print('first')"
  - id: step-2
    command: python -c "print('second')"
    depends_on: step-1
"""
    # 1. Start execution and run only step-1
    state = WorkflowPlanner.plan_workflow(yaml_wf)
    executor = WorkflowExecutor(state)
    state.start()
    
    # Run step-1 only
    success = executor.run_step("step-1")
    assert success is True
    assert state.steps["step-1"]["status"] == "succeeded"
    assert state.steps["step-2"]["status"] == "pending"

    # Persist the state to simulate interruption
    state_file = tmp_path / "interrupted.state.json"
    state.persist(state_file)

    # 2. Re-load the state from disk
    loaded_state = StateEngine.load_from_json(state_file)
    assert loaded_state.steps["step-1"]["status"] == "succeeded"
    assert loaded_state.steps["step-2"]["status"] == "pending"

    # 3. Resume execution using a new executor instance
    new_executor = WorkflowExecutor(loaded_state)
    
    # Track steps that got executed by mocking run_step
    executed_steps = []
    original_run_step = new_executor.run_step
    
    def mock_run_step(step_id):
        executed_steps.append(step_id)
        return original_run_step(step_id)
        
    new_executor.run_step = mock_run_step
    new_executor.execute_all()

    # Verify step-1 was skipped and step-2 was executed
    assert "step-1" not in executed_steps
    assert "step-2" in executed_steps
    assert loaded_state.status == "succeeded"
    assert loaded_state.steps["step-2"]["status"] == "succeeded"


def test_workflow_recovery_resets_running_steps(tmp_path):
    """Verify that steps interrupted mid-execution (left in 'running' state) are reset and rerun."""
    yaml_wf = """
name: "Recovery Test"
steps:
  - id: step-1
    command: python -c "print('recovered')"
"""
    state = WorkflowPlanner.plan_workflow(yaml_wf)
    
    # Simulate a crash where step-1 was left in "running" status
    state.status = "running"
    state.steps["step-1"]["status"] = "running"
    state.steps["step-1"]["starts_at"] = "2026-07-18T12:00:00Z"
    
    state_file = tmp_path / "crashed.state.json"
    state.persist(state_file)

    # Load and execute recovery
    loaded_state = StateEngine.load_from_json(state_file)
    executor = WorkflowExecutor(loaded_state)
    
    executor.execute_all()

    # Verify step-1 was successfully rerun and completed
    assert loaded_state.steps["step-1"]["status"] == "succeeded"
    assert loaded_state.status == "succeeded"
