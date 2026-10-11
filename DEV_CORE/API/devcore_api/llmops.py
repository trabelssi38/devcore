from __future__ import annotations

import os
import json
import math
import re
import threading
from collections import deque
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


CaptureResult = Literal["buffered", "sent", "dropped", "invalid"]


class LlmOpsClient:
    def __init__(self, *, transport: Callable[[dict[str, Any]], None] | None = None,
                 max_events: int = 256, max_bytes: int = 1024 * 1024) -> None:
        if type(max_events) is not int or not 1 <= max_events <= 4096:
            raise ValueError('Invalid event capacity')
        if type(max_bytes) is not int or not 1024 <= max_bytes <= 16 * 1024 * 1024:
            raise ValueError('Invalid byte capacity')
        self.transport = transport
        self.max_events, self.max_bytes = max_events, max_bytes
        self._buffer = deque()
        self._bytes = 0
        self._lock = threading.Lock()
        self._counts = dict.fromkeys(('sent', 'dropped', 'invalid', 'transport_errors'), 0)

    @property
    def buffered_events(self) -> list[LangfuseEvent]:
        with self._lock:
            return [event for event, _ in self._buffer]

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {'buffered': len(self._buffer), 'buffered_bytes': self._bytes,
                'max_events': self.max_events, 'max_bytes': self.max_bytes, **self._counts}

    def _count(self, key):
        self._counts[key] = min((1 << 63) - 1, self._counts[key] + 1)

    def _retain(self, event, size):
        with self._lock:
            if len(self._buffer) >= self.max_events or self._bytes + size > self.max_bytes:
                self._count('dropped')
                return 'dropped'
            self._buffer.append((event, size))
            self._bytes += size
        return 'buffered'

    @staticmethod
    def _payload(event):
        if type(event) is not LangfuseEvent or type(event.usage) is not LlmUsage:
            raise ValueError('Invalid event schema')
        for value in (event.name, event.model, event.trace_id):
            if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,128}', value):
                raise ValueError('Invalid event identifier')
        for value in (event.run_id, event.task_id, event.project_id):
            if value is not None and (not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,128}', value)):
                raise ValueError('Invalid correlation identifier')
        usage = event.usage
        if any(type(value) is not int or not 0 <= value <= (1 << 63) - 1 for value in
               (usage.prompt_tokens, usage.completion_tokens, usage.total_tokens)):
            raise ValueError('Invalid token usage')
        if usage.total_tokens != usage.prompt_tokens + usage.completion_tokens:
            raise ValueError('Inconsistent token usage')
        if type(usage.cost_usd) not in (int, float) or not 0 <= usage.cost_usd <= 1e9:
            raise ValueError('Invalid cost')
        if not math.isfinite(usage.cost_usd):
            raise ValueError('Invalid cost')
        payload = event.as_langfuse_payload()
        size = len(json.dumps(payload, allow_nan=False).encode('utf-8'))
        if size > 4096:
            raise ValueError('Oversized event')
        return payload, size

    @property
    def configured(self) -> bool:
        return bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"))

    def capture(self, event: LangfuseEvent) -> CaptureResult:
        try:
            payload, size = self._payload(event)
        except (ValueError, TypeError, OverflowError):
            with self._lock:
                self._count('invalid')
            return 'invalid'
        if not self.configured or self.transport is None:
            return self._retain(event, size)
        try:
            self.transport(payload)
        except Exception:
            # No raw exception text, secrets, retry or workflow failure.
            with self._lock:
                self._count('transport_errors')
            return self._retain(event, size)
        with self._lock:
            self._count('sent')
        return "sent"
