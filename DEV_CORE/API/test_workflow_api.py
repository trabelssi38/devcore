import os
import sys
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure devcore_api package is in path
api_dir = Path(__file__).resolve().parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from devcore_api.app import create_app


@pytest.fixture
def mock_data_root(tmp_path, monkeypatch):
    """Patch DEVCORE_DATA_ROOT to a temporary path for isolated file operations."""
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path))
    from devcore_api import ports
    monkeypatch.setattr(ports, "default_data_root", lambda: tmp_path)
    return tmp_path


def test_list_workflows_empty(mock_data_root):
    """Verify listing workflows returns empty list when directory does not exist or has no files."""
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/api/v1/workflows")
    assert response.status_code == 200
    assert response.json() == {"workflows": []}


def test_get_workflow_not_found(mock_data_root):
    """Verify GET workflow run details returns a 404 error when workflow does not exist."""
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/api/v1/workflows/wf-unknown")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "workflow_not_found"


def test_workflow_api_nominal_flow(mock_data_root):
    """Verify workflow list, get, and metrics output reflect persisted workflow state."""
    app = create_app()
    client = TestClient(app)

    # 1. Create a mock state file
    workflows_dir = mock_data_root / "Workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    
    mock_workflow = {
        "run_id": "wf-12345",
        "name": "Platform Boot",
        "description": "Bootstrap services",
        "status": "succeeded",
        "created_at": "2026-07-18T10:00:00Z",
        "started_at": "2026-07-18T10:01:00Z",
        "completed_at": "2026-07-18T10:02:00Z",
        "step_definitions": [
            {"id": "step-1", "title": "Check Qdrant"}
        ],
        "steps": {
            "step-1": {
                "id": "step-1",
                "status": "succeeded",
                "starts_at": "2026-07-18T10:01:05Z",
                "completed_at": "2026-07-18T10:01:50Z"
            }
        }
    }
    
    state_file = workflows_dir / "wf-12345.state.json"
    state_file.write_text(json.dumps(mock_workflow), encoding="utf-8")

    # 2. Test list workflows
    list_resp = client.get("/api/v1/workflows")
    assert list_resp.status_code == 200
    workflows = list_resp.json()["workflows"]
    assert len(workflows) == 1
    assert workflows[0]["run_id"] == "wf-12345"
    assert workflows[0]["name"] == "Platform Boot"
    assert workflows[0]["status"] == "succeeded"

    # 3. Test get workflow details
    detail_resp = client.get("/api/v1/workflows/wf-12345")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["run_id"] == "wf-12345"
    assert detail["steps"]["step-1"]["status"] == "succeeded"

    # 4. Test metrics integration
    metrics_resp = client.get("/api/v1/metrics")
    assert metrics_resp.status_code == 200
    assert "devcore_workflows_total" in metrics_resp.text
    assert 'name="Platform Boot",status="succeeded"} 1' in metrics_resp.text
