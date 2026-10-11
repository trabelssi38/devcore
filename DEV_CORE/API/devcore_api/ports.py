import json
import os
import sqlite3
import logging
import tempfile
from pathlib import Path
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from .contracts import (
    HealthContract,
    KnowledgeItemContract,
    ModelRequestContract,
    ModelResponseContract,
    RunContract,
    RunnerResultContract,
    TaskContract,
    UserContract,
    WorkspaceMembershipContract,
)


class TaskBoardNotFound(FileNotFoundError):
    pass


class TaskBoardInvalid(ValueError):
    pass


@runtime_checkable
class TaskRepository(Protocol):
    def list_tasks(self, project: str) -> list[TaskContract]:
        ...


@runtime_checkable
class HealthPort(Protocol):
    def get_health(self) -> HealthContract:
        ...


@runtime_checkable
class UnitOfWork(Protocol):
    def __enter__(self) -> "UnitOfWork":
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...


@runtime_checkable
class IdentityProvider(Protocol):
    def get_user(self, user_id: str) -> UserContract | None:
        ...

    def validate_token(self, token: str) -> UserContract | None:
        ...

    def get_membership(
        self, workspace_id: str, user_id: str
    ) -> WorkspaceMembershipContract | None:
        ...


@runtime_checkable
class WorkflowEngine(Protocol):
    def start_run(self, task_id: str, context: object | None = None) -> RunContract:
        ...

    def get_run(self, run_id: str) -> RunContract | None:
        ...

    def cancel_run(self, run_id: str) -> RunContract:
        ...


@runtime_checkable
class Runner(Protocol):
    def execute(
        self, command: str, run_id: str, timeout_seconds: float | None = None
    ) -> RunnerResultContract:
        ...


@runtime_checkable
class ModelGateway(Protocol):
    def generate(
        self, request: ModelRequestContract | str, model: str | None = None
    ) -> ModelResponseContract:
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


@runtime_checkable
class KnowledgeProvider(Protocol):
    def search(
        self, query: str, project: str, limit: int = 10
    ) -> list[KnowledgeItemContract]:
        ...

    def get_context(self, project: str, budget_bytes: int = 12000) -> str:
        ...


class InMemoryUnitOfWork:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    def __enter__(self) -> "InMemoryUnitOfWork":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        if exc_type is not None:
            self.rollback()

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class SqliteUnitOfWork:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def __enter__(self) -> "SqliteUnitOfWork":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        if exc_type is not None:
            self.rollback()

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()


def default_data_root() -> Path:
    return Path(os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[3] / "DEV_CORE_DATA")))


def validate_project_id(project: str) -> str:
    value = str(project or "").strip()
    if not value or "/" in value or "\\" in value or ":" in value or ".." in value:
        raise ValueError(f"Invalid project id: {project}")
    return value


def canonical_task_status(status: str | None) -> str:
    return "active" if status == "in_progress" else str(status or "todo")


def normalize_status_filter(status: str | None) -> str | None:
    """Normalize status filter input: accepts both 'active' and 'in_progress'."""
    if status is None:
        return None
    val = str(status).strip().lower()
    return "active" if val in {"active", "in_progress"} else val


def canonical_db_status(status: str | None) -> str:
    """Map canonical API status to database storage status."""
    val = str(status or "").strip().lower()
    return "in_progress" if val == "active" else val


class FileTaskRepository:
    """Compatibility import/export adapter for legacy tasks.json task boards."""

    def __init__(self, data_root: Path | str | None = None) -> None:
        self.data_root = Path(data_root) if data_root is not None else default_data_root()

    def board_path(self, project: str) -> Path:
        safe_project = validate_project_id(project)
        return self.data_root / "Memory" / safe_project / "tasks.json"

    def import_compatibility_board(
        self,
        project: str,
        source_path: Path | str | None = None,
    ) -> list[TaskContract]:
        safe_project = validate_project_id(project)
        board_path = Path(source_path) if source_path is not None else self.board_path(safe_project)
        if not board_path.exists():
            raise TaskBoardNotFound(str(board_path))
        try:
            board = json.loads(board_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise TaskBoardInvalid("Task board is not valid JSON") from exc
        if not isinstance(board, dict) or board.get("project") != safe_project:
            raise TaskBoardInvalid("Task board project does not match requested project")
        board_project = safe_project
        if not isinstance(board.get("tasks"), list):
            raise TaskBoardInvalid("Task board tasks must be a list")
        if any(not isinstance(item, dict) or item.get("project", board_project) != board_project
               for item in board["tasks"]):
            raise TaskBoardInvalid("Task board contains a task from another project")
        return [
            TaskContract(
                id=str(item.get("id")),
                title=str(item.get("title") or ""),
                status=canonical_task_status(item.get("status")),
                mode=item.get("mode"),
                steps_done=int(item.get("steps_done", 0)),
                steps_total=int(item.get("steps_total", 1)),
                project=board_project,
                version=item.get("version"),
            )
            for item in board.get("tasks", [])
        ]

    def export_compatibility_board(
        self,
        project: str,
        tasks: list[TaskContract],
        current_task: str | None = None,
        target_path: Path | str | None = None,
    ) -> Path:
        safe_project = validate_project_id(project)
        dest_path = Path(target_path) if target_path is not None else self.board_path(safe_project)
        dest_dir = dest_path.parent
        dest_dir.mkdir(parents=True, exist_ok=True)

        if current_task is None:
            active_task = next(
                (t for t in tasks if canonical_task_status(t.status) == "active"), None
            )
            current_task = active_task.id if active_task else None

        board_obj = {
            "project": safe_project,
            "current_task": current_task,
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "status": task.status,
                    "mode": task.mode,
                    "steps_done": task.steps_done,
                    "steps_total": task.steps_total,
                    "version": task.version,
                    "project": safe_project,
                }
                for task in tasks
            ],
        }

        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=dest_dir,
                prefix=".tasks-compat-",
                suffix=".tmp",
                delete=False,
            ) as tmp:
                tmp_path = Path(tmp.name)
                json.dump(board_obj, tmp, indent=2, ensure_ascii=False)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_path, dest_path)
            tmp_path = None
            return dest_path
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)

    def list_tasks(self, project: str) -> list[TaskContract]:
        return self.import_compatibility_board(project)


class SqliteTaskRepository:
    """Read-only adapter for the local migration phase."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)

    def list_tasks(self, project: str) -> list[TaskContract]:
        project = validate_project_id(project)
        connection = sqlite3.connect(
            self.db_path.resolve().as_uri() + "?mode=ro", uri=True
        )
        connection.row_factory = sqlite3.Row
        try:
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(tasks)")}
            version_column = "version" if "version" in columns else "NULL AS version"
            rows = connection.execute(
                f"""SELECT id, title, status, mode, steps_done, steps_total, {version_column}
                   FROM tasks WHERE project_id = ? AND status <> 'deleted'
                   ORDER BY created_at, rowid""",
                (project,),
            ).fetchall()
            return [TaskContract(
                id=row["id"], title=row["title"],
                status=canonical_task_status(row["status"]), mode=row["mode"],
                steps_done=row["steps_done"], steps_total=row["steps_total"],
                project=project,
                version=row["version"],
            ) for row in rows]
        finally:
            connection.close()


class StaticHealthPort:
    def get_health(self) -> HealthContract:
        return HealthContract(status="ok", checks={"api": "ok"})


def default_task_read_mode() -> str:
    return os.environ.get("DEVCORE_TASK_READ_MODE", "json").strip().lower()


def configured_task_repository() -> TaskRepository:
    mode = default_task_read_mode()
    legacy = FileTaskRepository()
    if mode == "json":
        return legacy
    if mode not in {"sql", "dual"}:
        raise ValueError(f"Invalid task read mode: {mode}")
    db_path = os.environ.get("DEVCORE_SQLITE_DB_PATH", "").strip()
    if not db_path:
        raise ValueError("DEVCORE_SQLITE_DB_PATH is required for sql or dual task read mode")
    if not Path(db_path).is_file():
        raise FileNotFoundError(f"Configured SQLite database does not exist: {db_path}")
    return DualReadTaskRepository(
        legacy_repository=legacy,
        sql_repository=SqliteTaskRepository(db_path),
        mode=mode,
        on_mismatch=logging.getLogger("devcore_api.tasks").warning,
    )


def compare_task_fields(
    legacy_tasks: list[TaskContract],
    sql_tasks: list[TaskContract],
) -> dict[str, Any]:
    """Compare fields and versions between legacy and SQL task sources.

    Returns a structured dictionary detailing matches, missing tasks, field divergences,
    and version discrepancies.
    """
    legacy_by_id = {t.id: t for t in legacy_tasks}
    sql_by_id = {t.id: t for t in sql_tasks}

    missing_in_sql = [tid for tid in legacy_by_id if tid not in sql_by_id]
    missing_in_legacy = [tid for tid in sql_by_id if tid not in legacy_by_id]

    field_mismatches: list[dict[str, Any]] = []
    version_mismatches: list[dict[str, Any]] = []

    fields_to_compare = ("title", "status", "mode", "steps_done", "steps_total", "version")

    for tid in sorted(set(legacy_by_id.keys()) & set(sql_by_id.keys())):
        leg = legacy_by_id[tid]
        sql = sql_by_id[tid]
        diffs = {}
        for field in fields_to_compare:
            leg_val = getattr(leg, field)
            sql_val = getattr(sql, field)
            if leg_val != sql_val:
                diffs[field] = {"legacy": leg_val, "sql": sql_val}
        if diffs:
            field_mismatches.append({"id": tid, "differences": diffs})
        if leg.version != sql.version:
            version_mismatches.append(
                {"id": tid, "legacy_version": leg.version, "sql_version": sql.version}
            )

    is_match = (
        not missing_in_sql
        and not missing_in_legacy
        and not field_mismatches
    )

    return {
        "is_match": is_match,
        "count_legacy": len(legacy_tasks),
        "count_sql": len(sql_tasks),
        "missing_in_sql": missing_in_sql,
        "missing_in_legacy": missing_in_legacy,
        "field_mismatches": field_mismatches,
        "version_mismatches": version_mismatches,
    }


class DualReadTaskRepository:
    def __init__(
        self,
        *,
        legacy_repository: TaskRepository,
        sql_repository: TaskRepository,
        mode: str | None = None,
        on_mismatch: Callable[[str], None] | None = None,
        on_mismatch_report: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.legacy_repository = legacy_repository
        self.sql_repository = sql_repository
        self.mode = (mode or default_task_read_mode()).strip().lower()
        self.on_mismatch = on_mismatch
        self.on_mismatch_report = on_mismatch_report
        self.last_comparison: dict[str, Any] | None = None

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
                if self.on_mismatch:
                    self.on_mismatch(f"task_read_sql_unavailable: project={project}")
                return legacy_tasks
            self._report_mismatch(project=project, legacy_tasks=legacy_tasks, sql_tasks=sql_tasks)
            return legacy_tasks
        raise ValueError(f"Invalid task read mode: {self.mode}")

    def compare_tasks(self, project: str) -> dict[str, Any]:
        """Perform an explicit comparison of fields and versions across both repositories."""
        legacy_tasks = self.legacy_repository.list_tasks(project)
        sql_tasks = self.sql_repository.list_tasks(project)
        comparison = compare_task_fields(legacy_tasks, sql_tasks)
        self.last_comparison = comparison
        return comparison

    def _report_mismatch(
        self,
        *,
        project: str,
        legacy_tasks: list[TaskContract],
        sql_tasks: list[TaskContract],
    ) -> None:
        comparison = compare_task_fields(legacy_tasks, sql_tasks)
        self.last_comparison = comparison
        if comparison["is_match"]:
            return
        if self.on_mismatch_report:
            self.on_mismatch_report(comparison)
        if self.on_mismatch:
            self.on_mismatch(f"task_read_mismatch: project={project} legacy={len(legacy_tasks)} sql={len(sql_tasks)}")
