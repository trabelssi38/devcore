import asyncio
import time
import sys
from typing import Optional
from .agent_runner import AgentRunner, TaskSpec, ExecutionResult, RunnerStatus


class LocalProcessRunner(AgentRunner):
    """
    Local process runner adapter for AgentRunner interface.
    Executes task actions as isolated subprocesses with timeout and checkpoint management.
    """

    def __init__(self, default_cmd: Optional[str] = None):
        super().__init__(name="LocalProcessRunner", backend_type="process")
        self.default_cmd = default_cmd or f"{sys.executable} -c \"print('DEV_CORE Task Executed')\""

    async def has_active_task(self) -> bool:
        return self._current_task is not None

    async def build_prompt(self, task: TaskSpec) -> str:
        return task.prompt or f"Execute local command for {task.id}: {task.title}"

    async def run(self, task: TaskSpec) -> ExecutionResult:
        start_time = time.time()
        self._current_task = task
        cmd = task.metadata.get("command") or self.default_cmd
        
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=task.timeout)
                duration = time.time() - start_time
                output_str = stdout.decode("utf-8", errors="replace") if stdout else ""
                error_str = stderr.decode("utf-8", errors="replace") if stderr else None
                
                status = "success" if proc.returncode == 0 else "failed"
                return ExecutionResult(
                    task_id=task.id,
                    status=status,
                    output=output_str.strip(),
                    error=error_str.strip() if error_str else None,
                    duration_sec=round(duration, 3),
                    checkpoint_saved=True
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                duration = time.time() - start_time
                return ExecutionResult(
                    task_id=task.id,
                    status="timeout",
                    error=f"Task timed out after {task.timeout}s",
                    duration_sec=round(duration, 3)
                )
        except Exception as exc:
            duration = time.time() - start_time
            return ExecutionResult(
                task_id=task.id,
                status="failed",
                error=str(exc),
                duration_sec=round(duration, 3)
            )
        finally:
            self._current_task = None

    async def checkpoint(self, task_id: str) -> bool:
        return True

    async def report_status(self) -> RunnerStatus:
        active = await self.has_active_task()
        task_id = self._current_task.id if self._current_task else None
        return RunnerStatus(
            name=self.name,
            backend_type=self.backend_type,
            active=active,
            current_task_id=task_id,
            health="OK"
        )
