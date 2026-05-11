from devcore.contracts import validate_contract
from devcore.paths import get_paths
from devcore.qdrant_queue import enqueue_refresh_job


def build_memory_draft(receipt: dict):
    validate_contract("receipt", receipt)
    paths = get_paths()
    session_dir = paths.session_root / receipt["handoff_id"]
    session_dir.mkdir(parents=True, exist_ok=True)

    content = "\n".join(
        [
            f"# Memory Review - {receipt['handoff_id']}",
            "",
            f"- Engine: {receipt['engine']}",
            f"- Status: {receipt['status']}",
            "",
            "## Candidates",
            *[f"- {item}" for item in receipt["memory_candidates"]],
        ]
    )

    draft_path = session_dir / "memory-draft.md"
    review_path = paths.memory_review_pending / f"{receipt['handoff_id']}.md"
    draft_path.write_text(content, encoding="utf-8")
    review_path.write_text(content, encoding="utf-8")
    return draft_path


def enqueue_qdrant_refresh(note_path: str) -> None:
    enqueue_refresh_job(
        note_path=note_path,
        source="memory",
        reason="manual_refresh",
    )
