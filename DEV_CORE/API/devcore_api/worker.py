from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Literal, Protocol

from .contracts import RunStatus
from .observability import SpanRecorder, recorded_span


@dataclass(frozen=True)
class WorkerRun:
    id: str
    task_id: str
    status: RunStatus


class RunRepository(Protocol):
    def claim_next_queued(self) -> WorkerRun | None: ...
    def transition(self, run_id: str, action: str) -> None: ...


WorkerResult = Literal["idle", "paused", "succeeded", "failed", "timed_out"]


class Worker:
    def __init__(
        self,
        *,
        repository: RunRepository,
        handler: Callable[[WorkerRun], None],
        timeout_seconds: float | None = None,
        span_recorder: SpanRecorder | None = None,
    ):
        self.repository = repository
        self.handler = handler
        self.timeout_seconds = timeout_seconds
        self.span_recorder = span_recorder

    def run_once(self) -> WorkerResult:
        run = self.repository.claim_next_queued()
        if run is None:
            return "idle"
        if run.status == "paused":
            return "paused"

        with recorded_span(self.span_recorder, "worker.run", {"run_id": run.id, "task_id": run.task_id}):
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

    def resume_after_restart(self) -> int:
        resume = getattr(self.repository, "resume_interrupted", None)
        if resume is None:
            return 0
        return int(resume())
