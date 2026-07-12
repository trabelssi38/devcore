from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from .correlation import CorrelationContext


@dataclass(frozen=True)
class LlmUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float


@dataclass(frozen=True)
class LangfuseEvent:
    name: str
    model: str
    trace_id: str
    run_id: str | None
    task_id: str | None
    project_id: str | None
    usage: LlmUsage

    @classmethod
    def from_generation(
        cls,
        *,
        name: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        correlation: CorrelationContext,
    ) -> "LangfuseEvent":
        return cls(
            name=name,
            model=model,
            trace_id=correlation.trace_id,
            run_id=correlation.run_id,
            task_id=correlation.task_id,
            project_id=correlation.project_id,
            usage=LlmUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_usd=cost_usd,
            ),
        )

    def as_langfuse_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "traceId": self.trace_id,
            "model": self.model,
            "usage": {
                "input": self.usage.prompt_tokens,
                "output": self.usage.completion_tokens,
                "total": self.usage.total_tokens,
                "cost": self.usage.cost_usd,
            },
            "metadata": {
                "run_id": self.run_id,
                "task_id": self.task_id,
                "project_id": self.project_id,
            },
        }


CaptureResult = Literal["buffered", "sent"]


class LlmOpsClient:
    def __init__(self, *, transport: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.transport = transport
        self.buffered_events: list[LangfuseEvent] = []

    @property
    def configured(self) -> bool:
        return bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"))

    def capture(self, event: LangfuseEvent) -> CaptureResult:
        if not self.configured or self.transport is None:
            self.buffered_events.append(event)
            return "buffered"
        self.transport(event.as_langfuse_payload())
        return "sent"
