from .agent_runner import AgentRunner, TaskSpec, ExecutionResult, RunnerStatus


class HermesRunner(AgentRunner):
    """
    Placeholder adapter until a real Hermes daemon protocol is implemented.
    """

    def __init__(self, daemon_url: str = "http://127.0.0.1:20128"):
        super().__init__(name="HermesRunner", backend_type="hermes")
        self.daemon_url = daemon_url

    async def has_active_task(self) -> bool:
        return self._current_task is not None

    async def build_prompt(self, task: TaskSpec) -> str:
        prompt = task.prompt or task.title
        return f"[DEV_CORE Task {task.id}] Project: {task.project}\nMode: {task.mode}\nGoal: {prompt}"

    async def run(self, task: TaskSpec) -> ExecutionResult:
        return ExecutionResult(
            task_id=task.id,
            status="failed",
            error="Hermes execution backend is not implemented",
            checkpoint_saved=False,
        )

    async def checkpoint(self, task_id: str) -> bool:
        return False

    async def report_status(self) -> RunnerStatus:
        active = await self.has_active_task()
        task_id = self._current_task.id if self._current_task else None
        return RunnerStatus(
            name=self.name,
            backend_type=self.backend_type,
            active=active,
            current_task_id=task_id,
            health="DOWN"
        )
