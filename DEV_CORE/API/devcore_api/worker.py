from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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


WorkerResult = Literal["idle", "succeeded", "failed"]


class Worker:
    def __init__(self, *, repository: RunRepository, handler: Callable[[WorkerRun], None]):
        self.repository = repository
        self.handler = handler

    def run_once(self) -> WorkerResult:
        run = self.repository.claim_next_queued()
        if run is None:
            return "idle"

        self.repository.transition(run.id, "start")
        try:
            self.handler(run)
        except Exception:
            self.repository.transition(run.id, "fail")
            return "failed"

        self.repository.transition(run.id, "succeed")
        return "succeeded"
