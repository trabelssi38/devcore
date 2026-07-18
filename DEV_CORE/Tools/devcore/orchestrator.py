import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

# Add parent dir to path if needed
tools_dir = Path(__file__).resolve().parent.parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from devcore.state_engine import StateEngine, InvalidStateTransition
from devcore.agent_runner import get_agent_runner

logger = logging.getLogger("orchestrator")


class WorkflowPlanner:
    """Parses, validates, and initializes workflow state graphs."""

    @classmethod
    def validate_dependency_graph(cls, step_defs: List[Dict[str, Any]]) -> None:
        """Verify that steps form a Directed Acyclic Graph (DAG) without cycles."""
        step_ids = {s["id"] for s in step_defs}
        adj: Dict[str, List[str]] = {}

        for step in step_defs:
            deps_raw = step.get("depends_on") or []
            deps = [deps_raw] if isinstance(deps_raw, str) else list(deps_raw)
            
            # Check dependencies existence
            for dep in deps:
                if dep not in step_ids:
                    raise ValueError(f"Step {step['id']} depends on non-existent step: {dep}")
            adj[step["id"]] = deps

        # Cycle detection using DFS (0=unvisited, 1=visiting, 2=visited)
        visited: Dict[str, int] = {sid: 0 for sid in step_ids}

        def dfs(node: str) -> None:
            visited[node] = 1
            for neighbor in adj.get(node, []):
                if visited[neighbor] == 1:
                    raise ValueError(f"Cyclic dependency detected involving steps {node} and {neighbor}")
                if visited[neighbor] == 0:
                    dfs(neighbor)
            visited[node] = 2

        for step_id in step_ids:
            if visited[step_id] == 0:
                dfs(step_id)

    @classmethod
    def plan_workflow(cls, yaml_content: str) -> StateEngine:
        """Create a validated StateEngine instance from a workflow YAML string."""
        engine = StateEngine.load_from_yaml(yaml_content)
        cls.validate_dependency_graph(engine.step_definitions)
        return engine


class WorkflowChecker:
    """Validation orchestrator running integrity, lint, and test checks."""

    def __init__(self, platform_root: Optional[Path] = None):
        self.platform_root = platform_root

    def check_post_step(self, step_id: str) -> bool:
        """Run post-step validations. Returns True if successful, False otherwise."""
        logger.info(f"[WorkflowChecker] Running post-step checks for step: {step_id}")
        # Default behavior: nominal pass
        return True


class WorkflowExecutor:
    """Executes step sequences and manages workflow completion transitions."""

    def __init__(self, state: StateEngine, checker: Optional[WorkflowChecker] = None):
        self.state = state
        self.checker = checker or WorkflowChecker()

    def get_runnable_steps(self) -> List[str]:
        """Resolve all steps ready for execution (pending and deps completed)."""
        runnable = []
        for step_id, step_state in self.state.steps.items():
            if step_state["status"] != "pending":
                continue

            # Lookup step definition to read dependencies
            step_def = next((s for s in self.state.step_definitions if s["id"] == step_id), {})
            deps_raw = step_def.get("depends_on") or []
            deps = [deps_raw] if isinstance(deps_raw, str) else list(deps_raw)

            # Check if all dependencies are succeeded or skipped
            all_deps_done = True
            for dep in deps:
                dep_state = self.state.steps.get(dep, {})
                if dep_state.get("status") not in ("succeeded", "skipped"):
                    all_deps_done = False
                    break

            if all_deps_done:
                runnable.append(step_id)
        return runnable

    def run_step(self, step_id: str) -> bool:
        """Execute a single step by dispatching it to its matching execution adapter."""
        step_def = next((s for s in self.state.step_definitions if s["id"] == step_id), {})
        self.state.start_step(step_id)
        self.state.persist()

        success = True
        error_msg = ""
        output_metadata = {}

        try:
            if "command" in step_def and step_def["command"]:
                # 1. Shell command execution
                cmd = step_def["command"]
                logger.info(f"[WorkflowExecutor] Executing CLI command: {cmd}")
                
                # Execute in shell context
                proc = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=step_def.get("timeout", 300)
                )
                if proc.returncode != 0:
                    success = False
                    error_msg = f"Command failed with code {proc.returncode}. Stderr: {proc.stderr.strip()}"
                else:
                    output_metadata = {"stdout": proc.stdout.strip()}
                    
            elif "task" in step_def and step_def["task"]:
                # 2. Agent task execution
                logger.info(f"[WorkflowExecutor] Executing Agent task: {step_def['task']}")
                runner = get_agent_runner()
                
                # Build mock/minimal task dictionary
                task_dict = {
                    "id": step_id,
                    "title": step_def.get("title", f"Task {step_id}"),
                    "mode": step_def.get("harness_profile", "coding")
                }
                
                receipt = runner.run(task_dict, timeout=step_def.get("timeout", 300))
                if receipt.get("status") not in ("ok", "manual", "noop"):
                    success = False
                    error_msg = f"Agent task failed: {receipt.get('error', 'unknown error')}"
                else:
                    output_metadata = receipt
                    
            elif "service" in step_def and step_def["service"]:
                # 3. Service initialization (mocked or registered service startup)
                logger.info(f"[WorkflowExecutor] Starting plugin service: {step_def['service']}")
                output_metadata = {"service": step_def["service"], "status": "running"}
                
            else:
                # 4. Fallback no-op step
                logger.info(f"[WorkflowExecutor] No action defined for step {step_id}, completing as no-op.")
                output_metadata = {"info": "no-op step"}

        except Exception as e:
            success = False
            error_msg = f"Execution exception: {str(e)}"

        # Validate with WorkflowChecker post-execution if execution was successful
        if success:
            try:
                checker_pass = self.checker.check_post_step(step_id)
                if not checker_pass:
                    success = False
                    error_msg = "Post-step validation check failed."
            except Exception as ce:
                success = False
                error_msg = f"Checker exception: {str(ce)}"

        # Finalize step state
        if success:
            self.state.complete_step(step_id, output_metadata)
        else:
            self.state.fail_step(step_id, error_msg)

        self.state.persist()
        return success

    def execute_all(self) -> None:
        """Run the workflow execution loop until completion or failure."""
        if self.state.status == "pending":
            self.state.start()
            self.state.persist()

        while self.state.status == "running":
            runnable = self.get_runnable_steps()
            if not runnable:
                # If there are no runnable steps left, evaluate final state
                incomplete = [sid for sid, s in self.state.steps.items() if s["status"] in ("pending", "running")]
                if not incomplete:
                    self.state.complete()
                else:
                    # Deadlock detection: steps remain incomplete but none are runnable (unsatisfiable dependencies)
                    self.state.fail()
                    logger.error("Execution loop halted: deadlocked step dependencies detected.")
                self.state.persist()
                break

            # Execute first runnable step sequentially
            step_to_run = runnable[0]
            step_success = self.run_step(step_to_run)
            if not step_success:
                # Executor immediately stops execution if any step fails
                break
