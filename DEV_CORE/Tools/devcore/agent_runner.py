import os
import sys
import json
import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

# Ensure paths can be resolved
tools_dir = Path(__file__).resolve().parent.parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from devcore.paths import get_paths

logger = logging.getLogger("agent_runner")


class AgentRunner(ABC):
    """Abstract base class for all agent runners in DEV_CORE v10."""

    @abstractmethod
    def has_active_task(self) -> bool:
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

    def has_active_task(self) -> bool:
        if not self._is_enabled():
            return False
        # Read tasks.json from active project
        try:
            # We look for a project tasks.json
            # Find the active project dynamically
            from dc import get_active_project
            proj = get_active_project()
            tasks_file = self.data_root / "Memory" / proj / "tasks.json"
            if tasks_file.exists():
                board = json.loads(tasks_file.read_text(encoding="utf-8-sig"))
                tasks = board.get("tasks", [])
                return any(t.get("status") == "active" for t in tasks)
        except Exception:
            pass
        return False

    def build_prompt(self, task: dict) -> str:
        return f"# Hermes Execution prompt\nTask ID: {task.get('id')}\nTitle: {task.get('title')}"

    def run(self, task: dict, timeout: int = 300) -> dict:
        if not self._is_enabled():
            return {"status": "error", "error": "Hermes is disabled"}
        logger.info(f"[HermesRunner] Triggering execution slot for task {task.get('id')}")
        return {"status": "ok", "runner": "hermes", "task_id": task.get("id")}

    def checkpoint(self, task: dict) -> dict:
        return {"status": "ok", "runner": "hermes"}

    def report_status(self) -> dict:
        if self._is_enabled():
            return {"status": "OK", "backend": "hermes"}
        else:
            return {"status": "DOWN", "error": "Hermes daemon is disabled in settings.json", "backend": "hermes"}


class LocalProcessAgentRunner(AgentRunner):
    """Adapter running tasks locally in a separate subagent process."""

    def __init__(self, platform_root: Path):
        self.platform_root = platform_root

    def has_active_task(self) -> bool:
        # Mock active check
        return True

    def build_prompt(self, task: dict) -> str:
        return f"# Local execution prompt\nTask ID: {task.get('id')}\nTitle: {task.get('title')}"

    def run(self, task: dict, timeout: int = 300) -> dict:
        logger.info(f"[LocalProcessRunner] Executing task {task.get('id')} locally")
        return {"status": "ok", "runner": "local_process", "task_id": task.get("id")}

    def checkpoint(self, task: dict) -> dict:
        return {"status": "ok", "runner": "local_process"}

    def report_status(self) -> dict:
        return {"status": "OK", "backend": "local_process"}


class CodexManualAgentRunner(AgentRunner):
    """Adapter writing prompt instructions to file for manual execution."""

    def __init__(self, data_root: Path):
        self.data_root = data_root

    def has_active_task(self) -> bool:
        return True

    def build_prompt(self, task: dict) -> str:
        return f"# Manual Codex Instruction\nTask ID: {task.get('id')}\nTitle: {task.get('title')}\nPlease perform changes manually."

    def run(self, task: dict, timeout: int = 300) -> dict:
        task_id = task.get("id", "unknown")
        try:
            from devcore.paths import get_paths
            session_dir = get_paths().session_root / task_id
        except Exception:
            session_dir = self.data_root / "Sessions" / task_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        prompt_file = session_dir / "manual-instruction.md"
        prompt_file.write_text(self.build_prompt(task), encoding="utf-8")
        
        logger.info(f"[CodexManualRunner] Written instructions to {prompt_file}")
        return {"status": "manual", "runner": "codex_manual", "prompt_path": str(prompt_file)}

    def checkpoint(self, task: dict) -> dict:
        return {"status": "ok", "runner": "codex_manual"}

    def report_status(self) -> dict:
        return {"status": "OK", "backend": "codex_manual"}


class NoOpAgentRunner(AgentRunner):
    """No-op fallback runner."""

    def has_active_task(self) -> bool:
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
            return CodexManualAgentRunner(paths.data_root)
