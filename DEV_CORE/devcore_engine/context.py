"""Explicit context for a single project-scoped operation."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from uuid import uuid4


def validate_project_id(project_id: str) -> str:
    value = str(project_id or "").strip()
    if not value or "/" in value or "\\" in value or ":" in value or ".." in value:
        raise ValueError("invalid project_id")
    return value


def project_from_directory(directory: Path | None = None) -> str | None:
    """Resolve the nearest explicit project manifest for one working directory."""
    current = (directory or Path.cwd()).resolve()
    for root in (current, *current.parents):
        manifest = root / ".devcore" / "project.json"
        if not manifest.is_file():
            continue
        try:
            return validate_project_id(json.loads(manifest.read_text(encoding="utf-8-sig"))["name"])
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None
    return None


@dataclass(frozen=True, slots=True)
class RequestContext:
    project_id: str
    user_id: str | None = None
    session_id: str | None = None
    run_id: str | None = None
    trace_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", validate_project_id(self.project_id))
        for name in ("user_id", "session_id", "run_id", "trace_id"):
            value = getattr(self, name)
            if value is None and name != "trace_id":
                continue
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"invalid {name}")
            object.__setattr__(self, name, value.strip())
