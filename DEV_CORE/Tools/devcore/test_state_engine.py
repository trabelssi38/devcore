import sys
import json
import pytest
from pathlib import Path

# Ensure devcore is in path
tools_dir = Path(__file__).resolve().parent.parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from devcore.state_engine import StateEngine, InvalidStateTransition, StepDefinition, WorkflowDefinition


def test_yaml_workflow_loader():
    """Test loading and validation of workflows from YAML content."""
    valid_yaml = """
name: "Launch Platform"
description: "Starts background processes"
steps:
  - id: start-qdrant
    service: qdrant
    timeout: 60
  - id: populate-memory
    task: populate
    depends_on: start-qdrant
"""
    engine = StateEngine.load_from_yaml(valid_yaml)
    assert engine.name == "Launch Platform"
    assert engine.description == "Starts background processes"
    assert len(engine.step_definitions) == 2
    assert "start-qdrant" in engine.steps
    assert "populate-memory" in engine.steps
    assert engine.steps["start-qdrant"]["status"] == "pending"


def test_yaml_workflow_validation_failures():
    """Test that invalid YAML workflow definitions raise appropriate validation errors."""
    # Missing name
    invalid_yaml_1 = """
description: "No name"
steps:
  - id: step1
"""
    with pytest.raises(ValueError):
        StateEngine.load_from_yaml(invalid_yaml_1)

    # Empty steps list
    invalid_yaml_2 = """
name: "Empty Steps"
steps: []
"""
    with pytest.raises(ValueError):
        StateEngine.load_from_yaml(invalid_yaml_2)

    # Step missing ID
    invalid_yaml_3 = """
name: "Missing ID"
steps:
  - service: qdrant
"""
    with pytest.raises(ValueError):
        StateEngine.load_from_yaml(invalid_yaml_3)

    # Invalid ID pattern
    invalid_yaml_4 = """
name: "Invalid ID Pattern"
steps:
  - id: "step #1"
"""
    with pytest.raises(ValueError):
        StateEngine.load_from_yaml(invalid_yaml_4)


def test_state_transitions_nominal():
    """Test nominal success flow of workflow state transitions."""
    engine = StateEngine(name="Nominal Run")
    engine.add_step_definitions([
        {"id": "step-1", "title": "First step"},
        {"id": "step-2", "title": "Second step"}
    ])

    assert engine.status == "pending"

    # Start workflow
    engine.start()
    assert engine.status == "running"
    assert engine.started_at is not None

    # Step 1 execution
    engine.start_step("step-1")
    assert engine.steps["step-1"]["status"] == "running"
    assert engine.steps["step-1"]["starts_at"] is not None

    engine.complete_step("step-1", {"result": "success-1"})
    assert engine.steps["step-1"]["status"] == "succeeded"
    assert engine.steps["step-1"]["completed_at"] is not None
    assert engine.steps["step-1"]["output"] == {"result": "success-1"}

    # Step 2 execution
    engine.start_step("step-2")
    engine.complete_step("step-2")

    # Complete workflow
    engine.complete()
    assert engine.status == "succeeded"
    assert engine.completed_at is not None


def test_state_transitions_failures():
    """Test failure transition pathways in both workflow and step actions."""
    engine = StateEngine(name="Failure Run")
    engine.add_step_definitions([
        {"id": "step-1", "title": "First step"}
    ])

    # Cannot start step when workflow is pending
    with pytest.raises(InvalidStateTransition):
        engine.start_step("step-1")

    engine.start()
    engine.start_step("step-1")

    # Fail the step
    engine.fail_step("step-1", "Network timeout")
    assert engine.steps["step-1"]["status"] == "failed"
    assert engine.steps["step-1"]["error_message"] == "Network timeout"
    
    # Workflow status should automatically fail
    assert engine.status == "failed"
    assert engine.completed_at is not None

    # Cannot transition workflow from terminal state
    with pytest.raises(InvalidStateTransition):
        engine.start()


def test_state_transitions_cancel_and_pause():
    """Test pausing, resuming, and cancelling active workflows and steps."""
    engine = StateEngine(name="Pause and Cancel Run")
    engine.add_step_definitions([
        {"id": "step-1"},
        {"id": "step-2"}
    ])

    engine.start()
    engine.start_step("step-1")
    engine.complete_step("step-1")

    # Pause
    engine.pause()
    assert engine.status == "paused"

    # Cannot start step while paused
    with pytest.raises(InvalidStateTransition):
        engine.start_step("step-2")

    # Resume
    engine.resume()
    assert engine.status == "running"

    # Cancel
    engine.cancel()
    assert engine.status == "cancelled"
    assert engine.steps["step-2"]["status"] == "cancelled"


def test_state_persistence(tmp_path):
    """Test serializing and restoring state engines from disk."""
    engine = StateEngine(name="Persist Run")
    engine.add_step_definitions([
        {"id": "step-1"},
        {"id": "step-2"}
    ])
    engine.start()
    engine.start_step("step-1")
    engine.complete_step("step-1", {"value": 42})
    engine.skip_step("step-2", "Not needed")

    # Persist
    filepath = tmp_path / "test-run.json"
    engine.persist(filepath)
    assert filepath.exists()

    # Load back
    loaded = StateEngine.load_from_json(filepath)
    assert loaded.run_id == engine.run_id
    assert loaded.name == "Persist Run"
    assert loaded.status == "running"
    assert loaded.steps["step-1"]["status"] == "succeeded"
    assert loaded.steps["step-1"]["output"] == {"value": 42}
    assert loaded.steps["step-2"]["status"] == "skipped"
    assert loaded.steps["step-2"]["error_message"] == "Not needed"
