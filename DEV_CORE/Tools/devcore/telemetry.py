from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from devcore.paths import get_paths


def _append_jsonl(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")
    return path


def log_prepare_event(event: dict) -> Path:
    payload = {
        **event,
        "event_type": "prepare",
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }
    return _append_jsonl(get_paths().router_log_root / "prepare-events.jsonl", payload)


def log_outcome_event(event: dict) -> Path:
    payload = {
        **event,
        "event_type": "outcome",
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }
    return _append_jsonl(get_paths().router_log_root / "outcome-events.jsonl", payload)
