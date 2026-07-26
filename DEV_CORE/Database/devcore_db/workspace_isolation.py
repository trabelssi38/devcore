from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


WORKSPACE_ID_RE = re.compile(r"^wks_[A-Za-z0-9_-]+$")
QDRANT_COLLECTION_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class WorkspaceIsolationError(ValueError):
    """Raised when workspace-scoped storage would escape its boundary."""


def default_data_root() -> Path:
    return Path(os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[3] / "DEV_CORE_DATA")))


@dataclass(frozen=True)
class WorkspaceScope:
    workspace_id: str
    root: Path
    data: Path
    secrets: Path
    artifacts: Path
    indexes: Path

    def resolve(self, area: str, *parts: str) -> Path:
        roots = {
            "data": self.data,
            "secrets": self.secrets,
            "artifacts": self.artifacts,
            "indexes": self.indexes,
        }
        if area not in roots:
            raise WorkspaceIsolationError(f"unknown workspace area: {area}")

        candidate = roots[area].joinpath(*parts).resolve()
        allowed_root = roots[area].resolve()
        if candidate != allowed_root and allowed_root not in candidate.parents:
            raise WorkspaceIsolationError(f"path escapes outside workspace area: {area}")
        return candidate

    def qdrant_collection(self, base_collection: str) -> str:
        if not QDRANT_COLLECTION_RE.match(base_collection):
            raise WorkspaceIsolationError("base_collection must be alphanumeric, '_' or '-'")
        return f"{self.workspace_id}_{base_collection}"


def build_workspace_scope(workspace_id: str, data_root: str | Path | None = None) -> WorkspaceScope:
    if not WORKSPACE_ID_RE.match(workspace_id):
        raise WorkspaceIsolationError("workspace_id must match wks_<slug>")

    root = Path(data_root) if data_root is not None else default_data_root()
    workspace_root = (root / "Workspaces" / workspace_id).resolve()
    return WorkspaceScope(
        workspace_id=workspace_id,
        root=workspace_root,
        data=workspace_root / "Data",
        secrets=workspace_root / "Secrets",
        artifacts=workspace_root / "Artifacts",
        indexes=workspace_root / "Indexes",
    )


def ensure_workspace_scope(workspace_id: str, data_root: str | Path | None = None) -> WorkspaceScope:
    scope = build_workspace_scope(workspace_id, data_root=data_root)
    for path in [scope.data, scope.secrets, scope.artifacts, scope.indexes]:
        path.mkdir(parents=True, exist_ok=True)
    return scope

