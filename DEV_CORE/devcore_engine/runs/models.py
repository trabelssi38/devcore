"""Data models and exceptions for durable runs in DEV_CORE."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal


RunStatus = Literal[
    "queued",
    "running",
    "waiting_approval",
    "paused",
    "succeeded",
    "failed",
    "cancelled",
    "timed_out",
]


class RunNotFoundError(Exception):
    """Raised when a run cannot be found."""


class RunTransitionError(ValueError):
    """Raised when an invalid state transition is attempted."""


class RunFencingError(Exception):
    """Raised when a worker token mismatch occurs (delayed or zombie worker)."""


class RunQuotaExceededError(Exception):
    """Raised when run execution quota is exceeded."""


class RunBackpressureError(Exception):
    """Raised when queued runs exceed allowed backpressure limits."""


class EffectAlreadyInProgressError(Exception):
    """Raised when an external effect is already in-flight."""


@dataclass(slots=True)
class RunSubmission:
    project_id: str
    title: str
    command: list[str] | str
    task_id: str | None = None
    timeout_seconds: float = 300.0
    env: dict[str, str] = field(default_factory=dict)
    idempotency_key: str | None = None
    actor: str = "system"
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized_command(self) -> list[str]:
        if isinstance(self.command, str):
            import shlex
            return shlex.split(self.command)
        return list(self.command)


@dataclass(slots=True)
class RunRecord:
    id: str
    project_id: str
    title: str
    status: RunStatus
    command: list[str]
    timeout_seconds: float = 300.0
    task_id: str | None = None
    attempt_number: int = 0
    max_attempts: int = 3
    worker_token: str | None = None
    heartbeat_at: datetime | None = None
    cancellation_requested: bool = False
    output: str | None = None
    error: str | None = None
    exit_code: int | None = None
    idempotency_key: str | None = None
    actor: str = "system"
    env: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def is_terminal(self) -> bool:
        return self.status in {"succeeded", "failed", "cancelled", "timed_out"}

    def is_active(self) -> bool:
        return self.status in {"queued", "running", "waiting_approval"}


@dataclass(frozen=True, slots=True)
class RunQuotaConfig:
    global_max_running: int = 2
    project_max_running: int = 1
    max_queued_per_project: int = 50
    heartbeat_interval_seconds: float = 5.0
    heartbeat_timeout_seconds: float = 15.0
    output_limit_bytes: int = 65536
