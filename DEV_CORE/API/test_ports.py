import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def write_task_board(data_root: Path, project: str = "devcore") -> None:
    board_dir = data_root / "Memory" / project
    board_dir.mkdir(parents=True)
    (board_dir / "tasks.json").write_text(
        json.dumps(
            {
                "project": project,
                "current_task": "T-157",
                "tasks": [
                    {
                        "id": "T-157",
                        "title": "Ports",
                        "status": "active",
                        "mode": "coding",
                        "steps_done": 0,
                        "steps_total": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_file_task_repository_reads_existing_board(tmp_path):
    from devcore_api.ports import FileTaskRepository

    write_task_board(tmp_path)
    repository = FileTaskRepository(data_root=tmp_path)

    tasks = repository.list_tasks(project="devcore")

    assert len(tasks) == 1
    assert tasks[0].id == "T-157"
    assert tasks[0].project == "devcore"


def test_api_tasks_endpoint_uses_task_repository_port(tmp_path):
    from devcore_api import create_app
    from devcore_api.ports import FileTaskRepository

    write_task_board(tmp_path)
    app = create_app(task_repository=FileTaskRepository(data_root=tmp_path))
    client = TestClient(app)

    response = client.get("/api/v1/tasks?project=devcore")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == 1
    assert payload["project"] == "devcore"
    assert payload["tasks"][0]["id"] == "T-157"


def test_api_tasks_endpoint_reports_missing_board_as_stable_error(tmp_path):
    from devcore_api import create_app
    from devcore_api.ports import FileTaskRepository

    app = create_app(task_repository=FileTaskRepository(data_root=tmp_path))
    client = TestClient(app)

    response = client.get("/api/v1/tasks?project=missing")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "task_board_not_found"
    assert payload["trace_id"]
