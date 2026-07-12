import json
import os
from pathlib import Path
from collections.abc import Callable
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


def default_task_read_mode() -> str:
    return os.environ.get("DEVCORE_TASK_READ_MODE", "json").strip().lower()


class DualReadTaskRepository:
    def __init__(
        self,
        *,
        legacy_repository: TaskRepository,
        sql_repository: TaskRepository,
        mode: str | None = None,
        on_mismatch: Callable[[str], None] | None = None,
    ) -> None:
        self.legacy_repository = legacy_repository
        self.sql_repository = sql_repository
        self.mode = (mode or default_task_read_mode()).strip().lower()
        self.on_mismatch = on_mismatch

    def list_tasks(self, project: str) -> list[TaskContract]:
        if self.mode == "json":
            return self.legacy_repository.list_tasks(project)
        if self.mode == "sql":
            return self.sql_repository.list_tasks(project)
        if self.mode == "dual":
            legacy_tasks = self.legacy_repository.list_tasks(project)
            try:
                sql_tasks = self.sql_repository.list_tasks(project)
            except Exception:
                return legacy_tasks
            self._report_mismatch(project=project, legacy_tasks=legacy_tasks, sql_tasks=sql_tasks)
            return legacy_tasks
        raise ValueError(f"Invalid task read mode: {self.mode}")

    def _report_mismatch(
        self,
        *,
        project: str,
        legacy_tasks: list[TaskContract],
        sql_tasks: list[TaskContract],
    ) -> None:
        legacy_ids = [task.id for task in legacy_tasks]
        sql_ids = [task.id for task in sql_tasks]
        if legacy_ids == sql_ids:
            return
        if self.on_mismatch:
            self.on_mismatch(f"task_read_mismatch: project={project} legacy={len(legacy_tasks)} sql={len(sql_tasks)}")
