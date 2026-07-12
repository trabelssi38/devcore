import json
import os
from pathlib import Path
from typing import Protocol

from .contracts import HealthContract, TaskContract


class TaskBoardNotFound(FileNotFoundError):
    pass


class TaskRepository(Protocol):
    def list_tasks(self, project: str) -> list[TaskContract]:
        ...


class HealthPort(Protocol):
    def get_health(self) -> HealthContract:
        ...


def default_data_root() -> Path:
    return Path(os.environ.get("DEVCORE_DATA_ROOT", r"C:\devcore\DEV_CORE_DATA"))


def validate_project_id(project: str) -> str:
    value = str(project or "").strip()
    if not value or "/" in value or "\\" in value or ":" in value or ".." in value:
        raise ValueError(f"Invalid project id: {project}")
    return value


class FileTaskRepository:
    def __init__(self, data_root: Path | str | None = None) -> None:
        self.data_root = Path(data_root) if data_root is not None else default_data_root()

    def board_path(self, project: str) -> Path:
        safe_project = validate_project_id(project)
        return self.data_root / "Memory" / safe_project / "tasks.json"

    def list_tasks(self, project: str) -> list[TaskContract]:
        board_path = self.board_path(project)
        if not board_path.exists():
            raise TaskBoardNotFound(str(board_path))
        board = json.loads(board_path.read_text(encoding="utf-8-sig"))
        board_project = str(board.get("project") or project)
        return [
            TaskContract(
                id=str(item.get("id")),
                title=str(item.get("title") or ""),
                status=item.get("status"),
                mode=item.get("mode"),
                steps_done=int(item.get("steps_done", 0)),
                steps_total=int(item.get("steps_total", 1)),
                project=board_project,
            )
            for item in board.get("tasks", [])
        ]


class StaticHealthPort:
    def get_health(self) -> HealthContract:
        return HealthContract(status="ok", checks={"api": "ok"})
