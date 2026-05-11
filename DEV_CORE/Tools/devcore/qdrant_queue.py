from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from devcore.paths import get_paths


def _append_jsonl_durable(queue_path: Path, payload: dict) -> None:
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(payload) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def enqueue_refresh_job(note_path: str, source: str, reason: str) -> Path:
    payload = {
        "note_path": note_path,
        "source": source,
        "reason": reason,
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }
    queue_path = get_paths().qdrant_refresh_queue
    _append_jsonl_durable(queue_path, payload)
    return queue_path


def write_rebuild_manifest() -> Path:
    paths = get_paths()
    note_paths = sorted(str(path) for path in paths.canonical_memory_root.glob("*.md"))
    payload = {
        "source_root": str(paths.canonical_memory_root),
        "note_paths": note_paths,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    paths.qdrant_rebuild_manifest.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    return paths.qdrant_rebuild_manifest
