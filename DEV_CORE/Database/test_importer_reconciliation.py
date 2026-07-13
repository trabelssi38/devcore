import json
import sys
from pathlib import Path


DATABASE_ROOT = Path(__file__).resolve().parent
if str(DATABASE_ROOT) not in sys.path:
    sys.path.insert(0, str(DATABASE_ROOT))


class FakeSession:
    def __init__(self):
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)


def write_board(path: Path, tasks: list[dict], project: str = "devcore") -> None:
    path.write_text(
        json.dumps({"project": project, "current_task": None, "tasks": tasks}, indent=2),
        encoding="utf-8",
    )


def test_task_board_importer_inserts_project_and_valid_tasks(tmp_path) -> None:
    from devcore_db.importer import TaskBoardImporter

    board_path = tmp_path / "tasks.json"
    write_board(
        board_path,
        [
            {
                "id": "T-164",
                "title": "Import data",
                "status": "active",
                "mode": "coding",
                "steps_done": 0,
                "steps_total": 1,
                "depends_on": None,
                "worktree": "main",
            }
        ],
    )
    session = FakeSession()

    report = TaskBoardImporter(session).import_file(board_path, root_path="C:/devcore")

    assert report.project == "devcore"
    assert report.tasks_seen == 1
    assert report.tasks_imported == 1
    assert report.tasks_skipped == 0
    assert report.warnings == []
    assert [statement.table.name for statement in session.statements] == [
        "organizations",
        "users",
        "workspaces",
        "projects",
        "tasks",
    ]


def test_task_board_importer_reports_invalid_tasks_without_crashing(tmp_path) -> None:
    from devcore_db.importer import TaskBoardImporter

    board_path = tmp_path / "tasks.json"
    write_board(
        board_path,
        [
            {"id": "T-good", "title": "Good", "status": "todo", "mode": "coding"},
            {"id": "", "title": "Missing id", "status": "todo", "mode": "coding"},
            {"id": "T-bad", "title": "", "status": "invalid", "mode": "coding"},
        ],
    )
    session = FakeSession()

    report = TaskBoardImporter(session).import_file(board_path, root_path="C:/devcore")

    assert report.tasks_seen == 3
    assert report.tasks_imported == 1
    assert report.tasks_skipped == 2
    assert len(report.warnings) == 2
    assert report.as_dict()["status"] == "partial"
