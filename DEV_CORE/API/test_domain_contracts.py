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

    assert task.schema_version == 1
    assert run.task_id == "T-156"
    assert event.type == "TaskCreated"
    assert plugin.enabled is True
    assert health.status == "ok"
    assert user.email == "user@example.com"
    assert workspace.organization_id == "org_01"


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
