import sys
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError


API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def test_domain_contract_models_validate_required_fields():
    from devcore_api.contracts import (
        DomainEvent,
        HealthContract,
        OrganizationContract,
        PluginContract,
        RunContract,
        TaskContract,
        UserContract,
        WorkspaceMembershipContract,
        WorkspaceQuotaContract,
        WorkspaceContract,
    )

    task = TaskContract(id="T-156", title="Define contracts", status="active", mode="coding")
    run = RunContract(id="run-1", task_id=task.id, status="queued")
    event = DomainEvent(id="evt-1", type="TaskCreated", source="task_service")
    plugin = PluginContract(id="python-fastapi", name="Python FastAPI", enabled=True)
    health = HealthContract(status="ok")
    user = UserContract(id="usr_01", email="user@example.com", display_name="User Example")
    organization = OrganizationContract(id="org_01", name="DEV_CORE")
    workspace = WorkspaceContract(id="wks_01", organization_id=organization.id, name="Core Workspace")
    membership = WorkspaceMembershipContract(
        id="mem_01",
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner",
    )
    quota = WorkspaceQuotaContract(
        workspace_id=workspace.id,
        runs_per_day=100,
        model_tokens_per_day=1_000_000,
        storage_mb=1024,
    )

    assert task.schema_version == 1
    assert run.task_id == "T-156"
    assert event.type == "TaskCreated"
    assert plugin.enabled is True
    assert health.status == "ok"
    assert user.email == "user@example.com"
    assert workspace.organization_id == "org_01"
    assert membership.role == "owner"
    assert quota.storage_mb == 1024


def test_task_contract_rejects_invalid_status():
    from devcore_api.contracts import TaskContract

    try:
        TaskContract(id="T-156", title="Bad", status="invalid", mode="coding")
    except ValidationError as exc:
        assert "status" in str(exc)
    else:
        raise AssertionError("TaskContract should reject unknown status")


def test_contract_catalog_endpoint_and_openapi_components():
    from devcore_api import create_app

    client = TestClient(create_app())
    response = client.get("/api/v1/contracts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == 1
    assert payload["contracts"] == [
        "Task",
        "Run",
        "Event",
        "Plugin",
        "Health",
        "User",
        "Organization",
        "Workspace",
        "WorkspaceMembership",
        "WorkspaceQuota",
    ]

    openapi = client.get("/api/v1/openapi.json").json()
    schemas = openapi["components"]["schemas"]
    for name in [
        "TaskContract",
        "RunContract",
        "DomainEvent",
        "PluginContract",
        "HealthContract",
        "UserContract",
        "OrganizationContract",
        "WorkspaceContract",
        "WorkspaceMembershipContract",
        "WorkspaceQuotaContract",
    ]:
        assert name in schemas


def test_workspace_contract_rejects_invalid_status():
    from devcore_api.contracts import WorkspaceContract

    try:
        WorkspaceContract(id="wks_01", organization_id="org_01", name="Bad", status="invalid")
    except ValidationError as exc:
        assert "status" in str(exc)
    else:
        raise AssertionError("WorkspaceContract should reject unknown status")


def test_workspace_membership_rejects_invalid_role():
    from devcore_api.contracts import WorkspaceMembershipContract

    try:
        WorkspaceMembershipContract(
            id="mem_01",
            workspace_id="wks_01",
            user_id="usr_01",
            role="superadmin",
        )
    except ValidationError as exc:
        assert "role" in str(exc)
    else:
        raise AssertionError("WorkspaceMembershipContract should reject unknown role")


def test_workspace_quota_rejects_negative_limits():
    from devcore_api.contracts import WorkspaceQuotaContract

    try:
        WorkspaceQuotaContract(
            workspace_id="wks_01",
            runs_per_day=-1,
            model_tokens_per_day=1,
            storage_mb=1,
        )
    except ValidationError as exc:
        assert "runs_per_day" in str(exc)
    else:
        raise AssertionError("WorkspaceQuotaContract should reject negative limits")


def test_runner_model_and_knowledge_contracts():
    from devcore_api.contracts import (
        KnowledgeItemContract,
        ModelRequestContract,
        ModelResponseContract,
        RunnerResultContract,
    )

    runner_res = RunnerResultContract(run_id="run-42", exit_code=0, stdout="ok", duration_seconds=1.5)
    assert runner_res.schema_version == 1
    assert runner_res.run_id == "run-42"
    assert runner_res.exit_code == 0
    assert runner_res.duration_seconds == 1.5

    model_req = ModelRequestContract(prompt="hello world", model="gemini-2.0-flash", temperature=0.7)
    assert model_req.prompt == "hello world"
    assert model_req.temperature == 0.7

    model_res = ModelResponseContract(text="greetings", model="gemini-2.0-flash", usage={"total_tokens": 12})
    assert model_res.text == "greetings"
    assert model_res.usage["total_tokens"] == 12

    k_item = KnowledgeItemContract(id="k-100", project="devcore", title="Architecture", content="DevCore Multi-user", score=0.88)
    assert k_item.id == "k-100"
    assert k_item.project == "devcore"
    assert k_item.score == 0.88

    # Rejection of invalid limits
    try:
        RunnerResultContract(run_id="r1", exit_code=0, duration_seconds=-1.0)
    except ValidationError as exc:
        assert "duration_seconds" in str(exc)
    else:
        raise AssertionError("RunnerResultContract should reject negative duration")

    try:
        ModelRequestContract(prompt="test", temperature=3.5)
    except ValidationError as exc:
        assert "temperature" in str(exc)
    else:
        raise AssertionError("ModelRequestContract should reject temperature > 2.0")
