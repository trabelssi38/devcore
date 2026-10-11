import os
import sys
import json
import logging
import subprocess
from uuid import uuid4
from abc import ABC, abstractmethod
from pathlib import Path

# Ensure paths can be resolved
tools_dir = Path(__file__).resolve().parent.parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))
if str(tools_dir.parent) not in sys.path:
    sys.path.insert(0, str(tools_dir.parent))

from devcore.paths import get_paths
from devcore_engine.context import validate_project_id
from devcore_engine.db import get_local_data_root
from devcore_engine.services.tasks import TaskService

logger = logging.getLogger("agent_runner")


def _has_active_task(project_id: str) -> bool:
    project_id = validate_project_id(project_id)
    service = TaskService()
    try:
        return any(task["status"] == "in_progress" for task in service.get_board(project_id)["tasks"])
    finally:
        service.conn.close()


class AgentRunner(ABC):
    """Abstract base class for all agent runners in DEV_CORE v10."""

    @abstractmethod
    def has_active_task(self, project_id: str = None) -> bool:
        """Check if there is an active task in the current project context."""
        pass

    @abstractmethod
    def build_prompt(self, task: dict) -> str:
        """Build the instruction prompt for the agent runner based on task context."""
        pass

    @abstractmethod
    def run(self, task: dict, timeout: int = 300) -> dict:
        """Execute the task and return execution receipt metadata."""
        pass

    @abstractmethod
    def checkpoint(self, task: dict) -> dict:
        """Trigger state checkpoint preservation for the current task."""
        pass

    @abstractmethod
    def report_status(self) -> dict:
        """Report runner health status, returns e.g. {'status': 'OK/DEGRADED/DOWN'}."""
        pass


class HermesAgentRunner(AgentRunner):
    """Adapter running tasks via the legacy Hermes daemon engine."""

    def __init__(self, settings_path: Path, data_root: Path):
        self.settings_path = settings_path
        self.data_root = data_root

    def _is_enabled(self) -> bool:
        if not self.settings_path.exists():
            return True
        try:
            settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
            return settings.get("services", {}).get("hermes_daemon", True)
        except Exception:
            return True

    def has_active_task(self, project_id: str = None) -> bool:
        return False

    def build_prompt(self, task: dict) -> str:
        return f"# Hermes Execution prompt\nTask ID: {task.get('id')}\nTitle: {task.get('title')}"

    def run(self, task: dict, timeout: int = 300) -> dict:
        if not self._is_enabled():
            return {"status": "error", "error": "Hermes is disabled"}
        return {"status": "failed", "runner": "hermes", "task_id": task.get("id"),
                "error": "Hermes execution backend is not implemented"}

    def checkpoint(self, task: dict) -> dict:
        return {"status": "unsupported", "runner": "hermes", "checkpoint_saved": False}

    def report_status(self) -> dict:
        if self._is_enabled():
            return {"status": "DOWN", "backend": "hermes", "error": "Hermes execution backend is not implemented"}
        else:
            return {"status": "DOWN", "error": "Hermes daemon is disabled in settings.json", "backend": "hermes"}


class LocalProcessAgentRunner(AgentRunner):
    """Adapter running tasks locally in a separate subagent process."""

    def __init__(self, platform_root: Path):
        self.platform_root = platform_root

    def has_active_task(self, project_id: str = None) -> bool:
        return False

    def build_prompt(self, task: dict) -> str:
        return f"# Local execution prompt\nTask ID: {task.get('id')}\nTitle: {task.get('title')}"

    def run(self, task: dict, timeout: int = 300) -> dict:
        return {"status": "failed", "runner": "local_process", "task_id": task.get("id"),
                "error": "Legacy local execution backend is not implemented"}

    def checkpoint(self, task: dict) -> dict:
        return {"status": "unsupported", "runner": "local_process", "checkpoint_saved": False}

    def report_status(self) -> dict:
        return {"status": "DOWN", "backend": "local_process", "error": "Legacy local execution backend is not implemented"}


class CodexManualAgentRunner(AgentRunner):
    """Adapter writing prompt instructions to file for manual execution."""

    def __init__(self, data_root: Path, session_root: Path = None):
        self.data_root = data_root
        self.session_root = session_root

    def has_active_task(self, project_id: str = None) -> bool:
        return _has_active_task(project_id)

    def build_prompt(self, task: dict) -> str:
        return f"# Manual Codex Instruction\nProject: {task.get('project_id')}\nTask ID: {task.get('id')}\nTitle: {task.get('title')}\nPlease perform changes manually."

    def run(self, task: dict, timeout: int = 300) -> dict:
        project_id = validate_project_id(task.get("project_id"))
        task_id = validate_project_id(task.get("id"))
        session_root = self.session_root or get_local_data_root() / "Sessions"
        session_dir = session_root / project_id / task_id / str(uuid4())
        session_dir.mkdir(parents=True, exist_ok=True)
        
        prompt_file = session_dir / "manual-instruction.md"
        prompt_file.write_text(self.build_prompt(task), encoding="utf-8")
        
        logger.info(f"[CodexManualRunner] Written instructions to {prompt_file}")
        return {"status": "manual", "runner": "codex_manual", "project_id": project_id,
                "task_id": task_id, "prompt_path": str(prompt_file), "executed": False}

    def checkpoint(self, task: dict) -> dict:
        return {"status": "unsupported", "runner": "codex_manual", "checkpoint_saved": False}

    def report_status(self) -> dict:
        return {"status": "OK", "backend": "codex_manual"}


class NoOpAgentRunner(AgentRunner):
    """No-op fallback runner."""

    def has_active_task(self, project_id: str = None) -> bool:
        return False

    def build_prompt(self, task: dict) -> str:
        return ""

    def run(self, task: dict, timeout: int = 300) -> dict:
        return {"status": "noop", "runner": "noop"}

    def checkpoint(self, task: dict) -> dict:
        return {"status": "noop", "runner": "noop"}

    def report_status(self) -> dict:
        return {"status": "OK", "backend": "noop"}


def get_agent_runner() -> AgentRunner:
    """Factory to instantiate the active AgentRunner based on configuration."""
    paths = get_paths()
    settings_path = paths.platform_root / "Config" / "settings.json"
    
    backend = "devcore"
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            backend = settings.get("scheduler_backend", "devcore")
            # If backend is devcore, we look at settings or environment to decide runner type
            # e.g., if we run inside docker container, we use LocalProcessAgentRunner
            # On host we can use CodexManualAgentRunner
        except Exception:
            pass
            
    # Check if hermes daemon is specifically disabled in settings
    is_hermes_enabled = True
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            is_hermes_enabled = settings.get("services", {}).get("hermes_daemon", True)
        except Exception:
            pass

    if backend == "hermes" and is_hermes_enabled:
        return HermesAgentRunner(settings_path, paths.data_root)
    else:
        # If running inside docker container (Linux), we use LocalProcessAgentRunner
        if os.name != "nt":
            return LocalProcessAgentRunner(paths.platform_root)
        else:
            return CodexManualAgentRunner(paths.data_root, session_root=paths.session_root)
