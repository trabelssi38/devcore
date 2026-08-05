import abc
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class TaskSpec:
    id: str
    project: str
    title: str
    mode: str = "coding"
    steps_total: int = 1
    steps_done: int = 0
    prompt: Optional[str] = None
    timeout: float = 300.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    task_id: str
    status: str  # "success", "failed", "timeout", "cancelled"
    output: str = ""
    error: Optional[str] = None
    duration_sec: float = 0.0
    checkpoint_saved: bool = False


@dataclass
class RunnerStatus:
    name: str
    backend_type: str
    active: bool = True
    current_task_id: Optional[str] = None
    health: str = "OK"  # "OK", "DEGRADED", "DOWN"
    last_check: str = field(default_factory=lambda: datetime.now().isoformat())


class AgentRunner(abc.ABC):
    """
    Abstract interface for Agent Runners in DEV_CORE.
    Isolates task execution engines (Hermes, Local Process, Codex, etc.) behind a unified contract.
    """

    def __init__(self, name: str, backend_type: str):
        self.name = name
        self.backend_type = backend_type
        self._current_task: Optional[TaskSpec] = None

    @abc.abstractmethod
    async def has_active_task(self) -> bool:
        """Return True if a task is currently executing on this runner."""
        pass

    @abc.abstractmethod
    async def build_prompt(self, task: TaskSpec) -> str:
        """Construct prompt payload for the given task."""
        pass

    @abc.abstractmethod
    async def run(self, task: TaskSpec) -> ExecutionResult:
        """Execute task asynchronously with safety timeout and result capture."""
        pass

    @abc.abstractmethod
    async def checkpoint(self, task_id: str) -> bool:
        """Create execution checkpoint for state preservation."""
        pass

    @abc.abstractmethod
    async def report_status(self) -> RunnerStatus:
        """Return current status, health, and active task info for the runner."""
        pass
