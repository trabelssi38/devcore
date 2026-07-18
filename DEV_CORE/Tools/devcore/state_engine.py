import os
import sys
import uuid
import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, Union, List, Dict, Any
import yaml
from pydantic import BaseModel, Field

# Add tools to sys path if needed
tools_dir = Path(__file__).resolve().parent.parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from devcore.paths import get_paths


class StepDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    title: Optional[str] = None
    service: Optional[str] = None
    task: Optional[str] = None
    command: Optional[str] = None
    harness_profile: Optional[str] = None
    timeout: Optional[int] = Field(None, ge=1)
    depends_on: Optional[Union[str, List[str]]] = None


class WorkflowDefinition(BaseModel):
    name: str = Field(min_length=1)
    description: Optional[str] = None
    steps: List[StepDefinition] = Field(min_length=1)


class InvalidStateTransition(ValueError):
    pass


class StateEngine:
    """State engine manager for DEV_CORE workflow executions."""

    def __init__(self, name: str, description: Optional[str] = None, run_id: Optional[str] = None):
        self.run_id = run_id or f"wf-{uuid.uuid4()}"
        self.name = name
        self.description = description or ""
        self.status = "pending"  # pending, running, paused, succeeded, failed, cancelled
        self.created_at = datetime.now(UTC).isoformat()
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        
        # Step runtime state mapping
        self.steps: Dict[str, Dict[str, Any]] = {}
        self.step_definitions: List[Dict[str, Any]] = []

    def add_step_definitions(self, step_defs: List[Dict[str, Any]]) -> None:
        self.step_definitions = step_defs
        for step in step_defs:
            self.steps[step["id"]] = {
                "id": step["id"],
                "status": "pending",  # pending, running, succeeded, failed, skipped, cancelled
                "starts_at": None,
                "completed_at": None,
                "error_message": None,
                "output": None
            }

    @classmethod
    def load_from_yaml(cls, yaml_content: str) -> 'StateEngine':
        """Load and validate workflow definition from YAML content."""
        try:
            parsed = yaml.safe_load(yaml_content)
        except Exception as e:
            raise ValueError(f"Invalid YAML format: {e}")

        # Validate with Pydantic contract
        defn = WorkflowDefinition(**parsed)

        # Build state engine instance
        engine = cls(name=defn.name, description=defn.description)
        engine.add_step_definitions([step.model_dump() for step in defn.steps])
        return engine

    def to_dict(self) -> Dict[str, Any]:
        """Serialize current state engine metadata."""
        return {
            "run_id": self.run_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "step_definitions": self.step_definitions,
            "steps": self.steps
        }

    def persist(self, filepath: Optional[Path] = None) -> Path:
        """Write the serialized state to disk."""
        if not filepath:
            paths = get_paths()
            # Ensure Workflows folder exists
            workflows_dir = paths.data_root / "Workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            filepath = workflows_dir / f"{self.run_id}.state.json"

        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return filepath

    @classmethod
    def load_from_json(cls, filepath: Path) -> 'StateEngine':
        """Restore state engine instance from serialized JSON."""
        data = json.loads(filepath.read_text(encoding="utf-8"))
        engine = cls(
            name=data["name"],
            description=data.get("description"),
            run_id=data["run_id"]
        )
        engine.status = data["status"]
        engine.created_at = data["created_at"]
        engine.started_at = data.get("started_at")
        engine.completed_at = data.get("completed_at")
        engine.step_definitions = data.get("step_definitions", [])
        engine.steps = data.get("steps", {})
        return engine

    # --- Transitions workflow ---

    def start(self) -> None:
        if self.status not in ("pending", "paused"):
            raise InvalidStateTransition(f"Cannot start workflow from state: {self.status}")
        self.status = "running"
        if not self.started_at:
            self.started_at = datetime.now(UTC).isoformat()

    def pause(self) -> None:
        if self.status != "running":
            raise InvalidStateTransition(f"Cannot pause workflow from state: {self.status}")
        self.status = "paused"

    def resume(self) -> None:
        if self.status != "paused":
            raise InvalidStateTransition(f"Cannot resume workflow from state: {self.status}")
        self.status = "running"

    def cancel(self) -> None:
        if self.status in ("succeeded", "failed", "cancelled"):
            raise InvalidStateTransition(f"Cannot cancel completed workflow from state: {self.status}")
        self.status = "cancelled"
        self.completed_at = datetime.now(UTC).isoformat()
        
        # Mark remaining active/pending steps as cancelled
        for step_id, step in self.steps.items():
            if step["status"] in ("pending", "running"):
                step["status"] = "cancelled"

    def complete(self) -> None:
        if self.status != "running":
            raise InvalidStateTransition(f"Cannot complete workflow from state: {self.status}")
        
        # Verify all steps are done (succeeded, skipped or cancelled)
        incomplete = [sid for sid, s in self.steps.items() if s["status"] in ("pending", "running")]
        if incomplete:
            raise InvalidStateTransition(f"Cannot complete workflow with incomplete steps: {incomplete}")

        self.status = "succeeded"
        self.completed_at = datetime.now(UTC).isoformat()

    def fail(self) -> None:
        if self.status not in ("running", "pending", "paused"):
            raise InvalidStateTransition(f"Cannot fail workflow from state: {self.status}")
        self.status = "failed"
        self.completed_at = datetime.now(UTC).isoformat()

    # --- Transitions steps ---

    def start_step(self, step_id: str) -> None:
        if self.status != "running":
            raise InvalidStateTransition("Workflow must be running to start a step.")
        if step_id not in self.steps:
            raise KeyError(f"Step {step_id} not found in workflow definition.")
        
        step = self.steps[step_id]
        if step["status"] != "pending":
            raise InvalidStateTransition(f"Cannot start step {step_id} from status {step['status']}")

        step["status"] = "running"
        step["starts_at"] = datetime.now(UTC).isoformat()

    def complete_step(self, step_id: str, output: Optional[Dict[str, Any]] = None) -> None:
        if self.status != "running":
            raise InvalidStateTransition("Workflow must be running to complete a step.")
        if step_id not in self.steps:
            raise KeyError(f"Step {step_id} not found in workflow definition.")
        
        step = self.steps[step_id]
        if step["status"] != "running":
            raise InvalidStateTransition(f"Cannot complete step {step_id} from status {step['status']}")

        step["status"] = "succeeded"
        step["completed_at"] = datetime.now(UTC).isoformat()
        step["output"] = output

    def fail_step(self, step_id: str, error_message: str) -> None:
        if self.status != "running":
            raise InvalidStateTransition("Workflow must be running to fail a step.")
        if step_id not in self.steps:
            raise KeyError(f"Step {step_id} not found in workflow definition.")
        
        step = self.steps[step_id]
        if step["status"] != "running":
            raise InvalidStateTransition(f"Cannot fail step {step_id} from status {step['status']}")

        step["status"] = "failed"
        step["completed_at"] = datetime.now(UTC).isoformat()
        step["error_message"] = error_message
        
        # Automatic workflow failure trigger
        self.fail()

    def skip_step(self, step_id: str, reason: Optional[str] = None) -> None:
        if self.status != "running":
            raise InvalidStateTransition("Workflow must be running to skip a step.")
        if step_id not in self.steps:
            raise KeyError(f"Step {step_id} not found in workflow definition.")
        
        step = self.steps[step_id]
        if step["status"] != "pending":
            raise InvalidStateTransition(f"Cannot skip step {step_id} from status {step['status']}")

        step["status"] = "skipped"
        step["completed_at"] = datetime.now(UTC).isoformat()
        step["error_message"] = reason
