import sys
from pathlib import Path
from fastapi.testclient import TestClient

API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from devcore_api import create_app
from devcore_api.contracts import TaskContract


class DummyTaskRepo:
    def __init__(self, tasks=None):
        self._tasks = tasks or []

    def list_tasks(self, project: str) -> list[TaskContract]:
        if project == "not_found":
            from devcore_api.ports import TaskBoardNotFound
            raise TaskBoardNotFound(f"Memory/{project}/tasks.json")
        return [t for t in self._tasks if t.project == project]


def _sample_tasks():
    return [
        TaskContract(id="T-01", title="Task 1", status="active", mode="coding", steps_done=0, steps_total=1, project="proj_alpha"),
        TaskContract(id="T-02", title="Task 2", status="todo", mode="reasoning", steps_done=0, steps_total=2, project="proj_alpha"),
        TaskContract(id="T-03", title="Task 3", status="done", mode="coding", steps_done=1, steps_total=1, project="proj_alpha"),
        TaskContract(id="T-04", title="Task 4", status="active", mode="bulk", steps_done=1, steps_total=5, project="proj_beta"),
    ]


def test_status_unification_active_and_in_progress():
    repo = DummyTaskRepo(_sample_tasks())
    app = create_app(task_repository=repo)
    client = TestClient(app)

    # Filtering by active
    res_active = client.get("/api/v1/tasks?project=proj_alpha&status=active")
    assert res_active.status_code == 200
    data_active = res_active.json()
    assert len(data_active["tasks"]) == 1
    assert data_active["tasks"][0]["id"] == "T-01"

    # Filtering by in_progress (synonym for active)
    res_in_prog = client.get("/api/v1/tasks?project=proj_alpha&status=in_progress")
    assert res_in_prog.status_code == 200
    data_in_prog = res_in_prog.json()
    assert len(data_in_prog["tasks"]) == 1
    assert data_in_prog["tasks"][0]["id"] == "T-01"

    # Filtering by todo
    res_todo = client.get("/api/v1/tasks?project=proj_alpha&status=todo")
    assert res_todo.status_code == 200
    data_todo = res_todo.json()
    assert len(data_todo["tasks"]) == 1
    assert data_todo["tasks"][0]["id"] == "T-02"


def test_pagination_and_metadata():
    repo = DummyTaskRepo(_sample_tasks())
    app = create_app(task_repository=repo)
    client = TestClient(app)

    # Page 1: limit 2, offset 0
    res_p1 = client.get("/api/v1/tasks?project=proj_alpha&limit=2&offset=0")
    assert res_p1.status_code == 200
    p1 = res_p1.json()
    assert len(p1["tasks"]) == 2
    assert p1["total_count"] == 3
    assert p1["offset"] == 0
    assert p1["limit"] == 2
    assert p1["has_more"] is True

    # Page 2: limit 2, offset 2
    res_p2 = client.get("/api/v1/tasks?project=proj_alpha&limit=2&offset=2")
    assert res_p2.status_code == 200
    p2 = res_p2.json()
    assert len(p2["tasks"]) == 1
    assert p2["total_count"] == 3
    assert p2["offset"] == 2
    assert p2["limit"] == 2
    assert p2["has_more"] is False

    # Validation errors on invalid pagination
    res_invalid = client.get("/api/v1/tasks?project=proj_alpha&limit=0")
    assert res_invalid.status_code == 422
    assert res_invalid.json()["error"]["code"] == "validation_error"


def test_route_catalog_endpoint():
    repo = DummyTaskRepo(_sample_tasks())
    app = create_app(task_repository=repo)
    client = TestClient(app)

    res = client.get("/api/v1/routes")
    assert res.status_code == 200
    data = res.json()
    assert data["schema_version"] == 1
    assert data["api_version"] == "v1"
    assert data["total_routes"] > 0

    paths = {r["path"] for r in data["routes"]}
    assert "/api/v1/routes" in paths
    assert "/api/v1/tasks" in paths
    assert "/api/v1/health" in paths
    assert "/api/v1/contracts" in paths
    assert "/api/tasks" in paths


def test_legacy_facades():
    repo = DummyTaskRepo(_sample_tasks())
    app = create_app(task_repository=repo)
    client = TestClient(app)

    # Legacy tasks facade
    res_tasks = client.get("/api/tasks?project=proj_alpha&status=in_progress")
    assert res_tasks.status_code == 200
    assert len(res_tasks.json()["tasks"]) == 1

    # Legacy health facade
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    # Legacy contracts facade
    res_contracts = client.get("/api/contracts")
    assert res_contracts.status_code == 200
    assert res_contracts.json()["api_version"] == "v1"

    # Legacy routes facade
    res_routes = client.get("/api/routes")
    assert res_routes.status_code == 200
    assert res_routes.json()["total_routes"] > 0


def test_unified_error_handling():
    repo = DummyTaskRepo()
    app = create_app(task_repository=repo)
    client = TestClient(app)

    # Missing project board (404)
    res_404 = client.get("/api/v1/tasks?project=not_found")
    assert res_404.status_code == 404
    err_404 = res_404.json()
    assert err_404["error"]["code"] == "task_board_not_found"
    assert err_404["trace_id"] != ""

    # Invalid project ID (400)
    res_400 = client.get("/api/v1/tasks?project=../bad_path")
    assert res_400.status_code == 400
    err_400 = res_400.json()
    assert err_400["error"]["code"] == "invalid_project"
    assert err_400["trace_id"] != ""
