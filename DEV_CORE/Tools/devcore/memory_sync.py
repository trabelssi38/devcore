from __future__ import annotations

import re

from devcore.paths import get_paths
from devcore.qdrant_queue import enqueue_refresh_job

_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def _validate_session_id(session_id: str) -> str:
    if not _SESSION_ID_PATTERN.fullmatch(session_id):
        raise ValueError(
            "session_id must contain only letters, numbers, underscores, and hyphens"
        )
    return session_id


def promote_approved_memory(session_id: str) -> dict:
    session_id = _validate_session_id(session_id)
    paths = get_paths()
    pending_path = paths.memory_review_pending / f"{session_id}.md"
    approved_path = paths.memory_review_approved / f"{session_id}.md"
    canonical_path = paths.canonical_memory_root / f"{session_id}.md"

    if not pending_path.exists():
        raise FileNotFoundError(str(pending_path))

    content = pending_path.read_text(encoding="utf-8")
    approved_path.write_text(content, encoding="utf-8")
    canonical_path.write_text(content, encoding="utf-8")
    enqueue_refresh_job(
        note_path=str(canonical_path),
        source="memory_sync",
        reason="approved_memory",
    )
    pending_path.unlink()

    return {
        "session_id": session_id,
        "approved_path": approved_path,
        "canonical_path": canonical_path,
    }
