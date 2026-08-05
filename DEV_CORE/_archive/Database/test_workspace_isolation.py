import sys
from pathlib import Path


DATABASE_ROOT = Path(__file__).resolve().parent
if str(DATABASE_ROOT) not in sys.path:
    sys.path.insert(0, str(DATABASE_ROOT))


def test_workspace_scope_declares_isolated_roots(tmp_path) -> None:
    from devcore_db.workspace_isolation import build_workspace_scope

    scope = build_workspace_scope("wks_alpha", data_root=tmp_path)

    assert scope.root == tmp_path / "Workspaces" / "wks_alpha"
    assert scope.data == scope.root / "Data"
    assert scope.secrets == scope.root / "Secrets"
    assert scope.artifacts == scope.root / "Artifacts"
    assert scope.indexes == scope.root / "Indexes"
    assert scope.qdrant_collection("codebase") == "wks_alpha_codebase"


def test_workspace_scope_rejects_path_traversal(tmp_path) -> None:
    from devcore_db.workspace_isolation import WorkspaceIsolationError, build_workspace_scope

    scope = build_workspace_scope("wks_alpha", data_root=tmp_path)

    try:
        scope.resolve("data", "..", "..", "wks_beta", "Secrets", "token.json")
    except WorkspaceIsolationError as exc:
        assert "outside workspace" in str(exc)
    else:
        raise AssertionError("workspace path traversal must be rejected")


def test_workspace_scope_rejects_unknown_workspace_id(tmp_path) -> None:
    from devcore_db.workspace_isolation import WorkspaceIsolationError, build_workspace_scope

    try:
        build_workspace_scope("../wks_beta", data_root=tmp_path)
    except WorkspaceIsolationError as exc:
        assert "workspace_id" in str(exc)
    else:
        raise AssertionError("invalid workspace_id must be rejected")


def test_workspace_scope_creates_directories_on_demand(tmp_path) -> None:
    from devcore_db.workspace_isolation import ensure_workspace_scope

    scope = ensure_workspace_scope("wks_alpha", data_root=tmp_path)

    for path in [scope.data, scope.secrets, scope.artifacts, scope.indexes]:
        assert path.is_dir()

