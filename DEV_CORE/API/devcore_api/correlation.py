from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from uuid import uuid4


def _header(headers: Mapping[str, str], name: str) -> str | None:
    lower_name = name.lower()
    for key, value in headers.items():
        if key.lower() == lower_name:
            cleaned = str(value or "").strip()
            return cleaned or None
    return None


@dataclass(frozen=True)
class CorrelationContext:
    trace_id: str
    run_id: str | None = None
    task_id: str | None = None
    project_id: str | None = None

    @classmethod
    def from_headers(cls, headers: Mapping[str, str]) -> "CorrelationContext":
        return cls(
            trace_id=_header(headers, "X-Trace-Id") or str(uuid4()),
            run_id=_header(headers, "X-Run-Id"),
            task_id=_header(headers, "X-Task-Id"),
            project_id=_header(headers, "X-Project-Id"),
        )

    def as_span_attributes(self) -> dict[str, str]:
        attributes = {"trace_id": self.trace_id}
        if self.run_id:
            attributes["run_id"] = self.run_id
        if self.task_id:
            attributes["task_id"] = self.task_id
        if self.project_id:
            attributes["project_id"] = self.project_id
        return attributes
