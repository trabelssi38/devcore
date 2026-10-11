"""Shared domain service for Cockpit and central API task mutations."""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Optional

from devcore_engine.context import RequestContext, validate_project_id
from devcore_engine.db import get_local_data_root
from devcore_engine.services.tasks import StaleTaskVersion, TaskService

SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def validate_safe_id(value: Any, label: str) -> str:
    s = str(value or "").strip()
    if (
        not SAFE_ID_PATTERN.fullmatch(s)
        or "/" in s
        or "\\" in s
        or ":" in s
        or ".." in s
    ):
        raise ValueError(f"Invalid {label}: {s}")
    return s


class TaskMutationConflict(RuntimeError):
    """The client acted on an older task version."""

    def __init__(self, message: str, code: str = "stale_task_version"):
        super().__init__(message)
        self.code = code


def resolve_db_path(db_path: Path | str | None = None) -> Path:
    if db_path is not None:
        return Path(db_path)
    return get_local_data_root() / "devcore.db"


def complete_task_usecase(
    project: str,
    task_id: str,
    expected_version: int | None = None,
    *,
    context: Optional[RequestContext] = None,
    db_path: Path | str | None = None,
) -> tuple[bool, str]:
    """Shared complete task usecase with version check and audit context."""
    try:
        project = validate_safe_id(project, "project")
        task_id = validate_safe_id(task_id, "task id")
        target_db = resolve_db_path(db_path)
        if not target_db.is_file():
            return False, f"Task database not found: {target_db}"

        with closing(sqlite3.connect(str(target_db), timeout=30.0)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            service = TaskService(conn)
            match = conn.execute(
                "SELECT * FROM tasks WHERE project_id = ? AND id = ? COLLATE NOCASE",
                (project, task_id),
            ).fetchone()
            if not match:
                return False, f"Task {task_id} not found in project {project}"
            if expected_version is not None and "version" not in match.keys():
                raise TaskMutationConflict(
                    "Task versions unavailable; migrate the database before conditional writes",
                    code="task_version_unavailable",
                )
            try:
                completed = service.complete_task(
                    match["id"],
                    project_id=project,
                    expected_version=expected_version,
                    context=context,
                )
            except StaleTaskVersion as exc:
                raise TaskMutationConflict(str(exc)) from exc

            if not completed:
                return False, f"Task {task_id} not found in project {project}"
            return True, f"Task {completed['id']} completed successfully"
    except TaskMutationConflict:
        raise
    except Exception as e:
        return False, str(e)


def transition_task_usecase(
    project: str,
    task_id: str,
    operation: str,
    expected_version: int | None = None,
    *,
    context: Optional[RequestContext] = None,
    db_path: Path | str | None = None,
) -> bool:
    """Shared task transition (pause/resume) usecase."""
    if operation not in {"pause", "resume"}:
        raise ValueError("Invalid transition")
    project = validate_safe_id(project, "project")
    task_id = validate_safe_id(task_id, "task id")
    target_db = resolve_db_path(db_path)
    with closing(
        sqlite3.connect(target_db.resolve().as_uri() + "?mode=rw", uri=True, timeout=30.0)
    ) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        service = TaskService(conn)
        match = conn.execute(
            "SELECT * FROM tasks WHERE project_id=? AND id=? COLLATE NOCASE AND status <> 'deleted'",
            (project, task_id),
        ).fetchone()
        if match is None:
            return False
        if "version" not in match.keys():
            raise TaskMutationConflict(
                "Task versions unavailable", code="task_version_unavailable"
            )
        if expected_version is not None and match["version"] != expected_version:
            raise TaskMutationConflict("Task version changed")
        try:
            method = getattr(service, operation + "_task")
            changed = method(
                match["id"],
                project,
                expected_version=expected_version,
                context=context,
            )
        except StaleTaskVersion as exc:
            raise TaskMutationConflict("Task version changed") from exc
        except ValueError as exc:
            raise TaskMutationConflict(
                "Task transition unavailable", code="task_transition_conflict"
            ) from exc
        if changed is None:
            raise TaskMutationConflict(
                "Task transition unavailable", code="task_transition_conflict"
            )
        return True


def delete_task_usecase(
    project: str,
    task_id: str,
    expected_version: int | None = None,
    *,
    context: Optional[RequestContext] = None,
    db_path: Path | str | None = None,
) -> tuple[bool, str]:
    """Shared delete task usecase with dependency validation."""
    try:
        project = validate_safe_id(project, "project")
        task_id = validate_safe_id(task_id, "task id")
        target_db = resolve_db_path(db_path)
        if not target_db.is_file():
            return False, f"Task database not found: {target_db}"

        with closing(sqlite3.connect(str(target_db), timeout=30.0)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            service = TaskService(conn)
            match = conn.execute(
                "SELECT * FROM tasks WHERE project_id = ? AND id = ? COLLATE NOCASE AND status <> 'deleted'",
                (project, task_id),
            ).fetchone()
            if not match:
                return False, f"Task {task_id} not found in project {project}"
            if expected_version is not None and "version" not in match.keys():
                raise TaskMutationConflict(
                    "Task versions unavailable; migrate the database before conditional writes",
                    code="task_version_unavailable",
                )
            try:
                deleted = service.delete_task(
                    match["id"],
                    project_id=project,
                    expected_version=expected_version,
                    context=context,
                )
            except StaleTaskVersion as exc:
                raise TaskMutationConflict(str(exc)) from exc
            except ValueError as exc:
                return False, str(exc)

            if not deleted:
                return False, f"Task {task_id} not found in project {project}"
            return True, f"Task {deleted['id']} deleted successfully"
    except TaskMutationConflict:
        raise
    except Exception as e:
        return False, str(e)
