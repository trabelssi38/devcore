import sys
import pytest
from pathlib import Path

# Ensure devcore is in path
tools_dir = Path(__file__).resolve().parent.parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from devcore.state_engine import StateEngine
from devcore.orchestrator import WorkflowPlanner, WorkflowExecutor, WorkflowChecker


def test_dependency_graph_cycle_detection():
    """Verify that WorkflowPlanner correctly identifies cyclic dependencies."""
    # 1. Valid acyclic DAG
    valid_defs = [
        {"id": "step-1", "depends_on": []},
        {"id": "step-2", "depends_on": ["step-1"]},
        {"id": "step-3", "depends_on": ["step-1"]}
    ]
    WorkflowPlanner.validate_dependency_graph(valid_defs)  # Should not raise

    # 2. Simple direct cycle (A -> B -> A)
    invalid_defs_1 = [
        {"id": "step-1", "depends_on": ["step-2"]},
        {"id": "step-2", "depends_on": ["step-1"]}
    ]
    with pytest.raises(ValueError) as exc:
        WorkflowPlanner.validate_dependency_graph(invalid_defs_1)
    assert "Cyclic dependency detected" in str(exc.value)

    # 3. Multi-node cycle (A -> B -> C -> A)
    invalid_defs_2 = [
        {"id": "step-1", "depends_on": ["step-3"]},
        {"id": "step-2", "depends_on": ["step-1"]},
        {"id": "step-3", "depends_on": ["step-2"]}
    ]
    with pytest.raises(ValueError) as exc:
        WorkflowPlanner.validate_dependency_graph(invalid_defs_2)
    assert "Cyclic dependency detected" in str(exc.value)

    # 4. Dependency on non-existent node
    invalid_defs_3 = [
        {"id": "step-1", "depends_on": ["missing-step"]}
    ]
    with pytest.raises(ValueError) as exc:
        WorkflowPlanner.validate_dependency_graph(invalid_defs_3)
    assert "depends on non-existent step" in str(exc.value)


def test_executor_runnable_steps_resolution():
    """Verify that WorkflowExecutor correctly evaluates execution order dependencies."""
    yaml_wf = """
name: "Dependency resolution"
steps:
  - id: step-a
  - id: step-b
    depends_on: step-a
  - id: step-c
    depends_on: step-a
"""
    state = WorkflowPlanner.plan_workflow(yaml_wf)
    executor = WorkflowExecutor(state)

    # At start, only step-a is runnable
    runnable = executor.get_runnable_steps()
    assert runnable == ["step-a"]

    # Start workflow and complete step-a
    state.start()
    state.start_step("step-a")
    state.complete_step("step-a")

    # Now step-b and step-c are runnable
    runnable = executor.get_runnable_steps()
    assert set(runnable) == {"step-b", "step-c"}


def test_command_step_execution_success(tmp_path):
    """Verify that WorkflowExecutor executes valid CLI commands and captures stdout."""
    yaml_wf = """
name: "Cli Success"
steps:
  - id: run-echo
    command: python -c "print('hello world')"
"""
    state = WorkflowPlanner.plan_workflow(yaml_wf)
    executor = WorkflowExecutor(state)

    # Persist mocks
    state_file = tmp_path / "test-run.state.json"
    state.persist(state_file)

    executor.execute_all()

    assert state.status == "succeeded"
    assert state.steps["run-echo"]["status"] == "succeeded"
    assert "hello world" in state.steps["run-echo"]["output"]["stdout"]


def test_command_step_execution_failure(tmp_path):
    """Verify that WorkflowExecutor handles non-zero exit codes correctly by failing the workflow."""
    yaml_wf = """
name: "Cli Failure"
steps:
  - id: run-fail
    command: python -c "import sys; sys.exit(42)"
"""
    state = WorkflowPlanner.plan_workflow(yaml_wf)
    executor = WorkflowExecutor(state)

    state_file = tmp_path / "test-run-fail.state.json"
    state.persist(state_file)

    executor.execute_all()

    assert state.status == "failed"
    assert state.steps["run-fail"]["status"] == "failed"
    assert "failed with code 42" in state.steps["run-fail"]["error_message"]


def test_executor_with_failed_checker(tmp_path):
    """Verify that step execution fails if the WorkflowChecker hook returns False."""
    yaml_wf = """
name: "Checker Failure"
steps:
  - id: run-step
    command: python -c "print('executed')"
"""
    state = WorkflowPlanner.plan_workflow(yaml_wf)
    
    # Custom checker that always rejects step validations
    class RejectingChecker(WorkflowChecker):
        def check_post_step(self, step_id: str) -> bool:
            return False

    executor = WorkflowExecutor(state, RejectingChecker())

    state_file = tmp_path / "test-run-checker.state.json"
    state.persist(state_file)

    executor.execute_all()

    assert state.status == "failed"
    assert state.steps["run-step"]["status"] == "failed"
    assert "validation check failed" in state.steps["run-step"]["error_message"]
