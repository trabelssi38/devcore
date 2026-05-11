from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DevCorePaths:
    platform_root: Path
    data_root: Path
    bus_root: Path
    session_root: Path
    vault_root: Path
    memory_root: Path
    memory_review_pending: Path
    memory_review_approved: Path
    canonical_memory_root: Path
    qdrant_refresh_queue: Path
    qdrant_rebuild_manifest: Path
    schema_root: Path
    router_log_root: Path
    scoring_log_root: Path


def _canonicalize_root(path_value: str) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.path.expanduser(path_value))))


def get_paths() -> DevCorePaths:
    platform_root = _canonicalize_root(
        os.environ.get("DEVCORE_PLATFORM_ROOT", r"C:\DEV_CORE")
    )
    data_root = _canonicalize_root(
        os.environ.get("DEVCORE_DATA_ROOT", r"C:\DEV_CORE_DATA")
    )

    bus_root = platform_root / "Bus"
    session_root = data_root / "Sessions"
    vault_root = data_root / "Vault"
    memory_root = data_root / "Memory"
    schema_root = platform_root / "Schemas"
    logs_root = data_root / "Logs"
    router_log_root = logs_root / "router"
    scoring_log_root = logs_root / "scoring"
    qdrant_refresh_queue = memory_root / "qdrant-refresh.jsonl"
    qdrant_rebuild_manifest = memory_root / "qdrant-rebuild-manifest.json"
    memory_review_pending = (
        vault_root / "05_AI" / "DEV_CORE" / "Memory Review" / "pending"
    )
    memory_review_approved = (
        vault_root / "05_AI" / "DEV_CORE" / "Memory Review" / "approved"
    )
    canonical_memory_root = vault_root / "05_AI" / "DEV_CORE" / "Memory"

    for directory in (
        bus_root / "drafts",
        bus_root / "receipts",
        bus_root / "archive",
        session_root,
        memory_root,
        memory_review_pending,
        memory_review_approved,
        canonical_memory_root,
        schema_root,
        router_log_root,
        scoring_log_root,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    return DevCorePaths(
        platform_root=platform_root,
        data_root=data_root,
        bus_root=bus_root,
        session_root=session_root,
        vault_root=vault_root,
        memory_root=memory_root,
        memory_review_pending=memory_review_pending,
        memory_review_approved=memory_review_approved,
        canonical_memory_root=canonical_memory_root,
        qdrant_refresh_queue=qdrant_refresh_queue,
        qdrant_rebuild_manifest=qdrant_rebuild_manifest,
        schema_root=schema_root,
        router_log_root=router_log_root,
        scoring_log_root=scoring_log_root,
    )
