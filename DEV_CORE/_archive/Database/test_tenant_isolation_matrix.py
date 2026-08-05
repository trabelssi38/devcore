import sys
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.dialects import postgresql


DATABASE_ROOT = Path(__file__).resolve().parent
API_ROOT = DATABASE_ROOT.parent / "API"
for import_root in (DATABASE_ROOT, API_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))


def compile_sql(statement) -> str:
    return str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


def test_tenant_isolation_matrix_covers_api_db_qdrant_and_artifacts(tmp_path) -> None:
    from devcore_api.contracts import WorkspaceContract
    from devcore_db.audit_log import AuditLogQuery, build_audit_log_select
    from devcore_db.workspace_isolation import WorkspaceIsolationError, build_workspace_scope

    alpha = build_workspace_scope("wks_alpha", data_root=tmp_path)
    beta = build_workspace_scope("wks_beta", data_root=tmp_path)

    assert WorkspaceContract(id="wks_alpha", organization_id="org_alpha", name="Alpha").id == "wks_alpha"
    try:
        WorkspaceContract(id="../wks_beta", organization_id="org_alpha", name="Bad")
    except ValidationError as exc:
        assert "id" in str(exc)
    else:
        raise AssertionError("API contracts must reject unsafe workspace ids")

    assert alpha.root != beta.root
    assert alpha.resolve("artifacts", "runs", "run-1.json").is_relative_to(alpha.artifacts.resolve())
    try:
        alpha.resolve("artifacts", "..", "..", "wks_beta", "Secrets", "token.json")
    except WorkspaceIsolationError as exc:
        assert "outside workspace" in str(exc)
    else:
        raise AssertionError("artifact paths must not cross workspace boundaries")

    assert alpha.qdrant_collection("decisions") == "wks_alpha_decisions"
    assert beta.qdrant_collection("decisions") == "wks_beta_decisions"
    assert alpha.qdrant_collection("decisions") != beta.qdrant_collection("decisions")
    for unsafe_collection in ("../decisions", "beta/decisions", "beta:decisions", ""):
        try:
            alpha.qdrant_collection(unsafe_collection)
        except WorkspaceIsolationError:
            pass
        else:
            raise AssertionError(f"unsafe qdrant collection accepted: {unsafe_collection}")

    sql = compile_sql(build_audit_log_select(AuditLogQuery(workspace_id="wks_alpha", project_id="devcore")))
    assert "JOIN projects" in sql
    assert "projects.workspace_id = 'wks_alpha'" in sql
    assert "audit_log.project_id = 'devcore'" in sql
