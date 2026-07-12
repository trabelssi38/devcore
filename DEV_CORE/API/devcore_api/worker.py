from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Literal, Protocol

from .contracts import RunStatus


@dataclass(frozen=True)
class WorkerRun:
    id: str
    task_id: str
    status: RunStatus


class RunRepository(Protocol):
    def claim_next_queued(self) -> WorkerRun | None: ...
    def transition(self, run_id: str, action: str) -> None: ...


WorkerResult = Literal["idle", "succeeded", "failed", "timed_out"]


class Worker:
    def __init__(self, *, repository: RunRepository, handler: Callable[[WorkerRun], None], timeout_seconds: float | None = None):
        self.repository = repository
        self.handler = handler
        self.timeout_seconds = timeout_seconds

    def run_once(self) -> WorkerResult:
        run = self.repository.claim_next_queued()
        if run is None:
            return "idle"

        self.repository.transition(run.id, "start")
        try:
            started = monotonic()
            self.handler(run)
            if self.timeout_seconds is not None and monotonic() - started >= self.timeout_seconds:
                self.repository.transition(run.id, "timeout")
                return "timed_out"
        except Exception:
            self.repository.transition(run.id, "fail")
            return "failed"

        self.repository.transition(run.id, "succeed")
        return "succeeded"
