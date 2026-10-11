"""SQL Repositories and Unit of Work for DEV_CORE target architecture.

Implements atomic task numbering, optimistic locking with stale version conflict detection,
UUID v5 global identities, and short transactions.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable, Iterable, Optional, Protocol, Union

from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError

from devcore_engine.persistence.models import projects, tasks
from devcore_engine.services.task_mutations import TaskMutationConflict

TASK_UUID_NAMESPACE = uuid.UUID("3bbec48a-1d88-524e-b9da-55e57b23a3c7")


def generate_task_uuid(project_id: str, identifier: str) -> uuid.UUID:
    """Generate a deterministic UUID v5 for a (project_id, identifier) pair."""
    return uuid.uuid5(TASK_UUID_NAMESPACE, f"{project_id}\x00{identifier}")


def parse_task_number(identifier: str) -> Optional[int]:
    """Parse numeric suffix from identifier such as T-01, T-1, task-42."""
    ident = identifier.strip()
    if ident.upper().startswith("T-"):
        part = ident[2:]
    elif ident.lower().startswith("task-"):
        part = ident[5:]
    else:
        part = ident
    try:
        return int(part)
    except ValueError:
        return None


class SessionLike(Protocol):
    """Protocol matching SQLAlchemy Session or database Connection."""
    def execute(self, statement: Any, params: Any = None) -> Any: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...


class SqlTaskRepository:
    """SQL repository for tasks enforcing atomic numbering and optimistic locking."""

    def __init__(self, session: Any) -> None:
        self.session = session

    def get_next_task_number(self, project_id: str) -> int:
        """Atomic calculation of the next task number within a project."""
        stmt = select(func.coalesce(func.max(tasks.c.task_number), 0) + 1).where(
            tasks.c.project_id == project_id
        )
        res = self.session.execute(stmt)
        if hasattr(res, "scalar"):
            val = res.scalar()
            return int(val) if val is not None else 1
        # Fallback for mock result wrappers
        return 1

    def create_task(
        self,
        *,
        project_id: str,
        title: str,
        mode: str = "coding",
        status: str = "todo",
        steps_total: int = 1,
        task_number: Optional[int] = None,
        legacy_id: Optional[str] = None,
        task_uuid: Optional[Union[uuid.UUID, str]] = None,
        depends_on_uuid: Optional[Union[uuid.UUID, str]] = None,
        worktree: Optional[str] = "main",
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Create a task with atomic numbering and UNIQUE(project_id, task_number)."""
        if not title or not title.strip():
            raise ValueError("Task title cannot be empty")

        auto_number = (task_number is None and legacy_id is None)

        # Attempt project row-level lock if supported by database dialect
        try:
            lock_stmt = select(projects.c.id).where(projects.c.id == project_id).with_for_update()
            self.session.execute(lock_stmt)
        except Exception:
            pass

        max_retries = 5 if auto_number else 1
        for attempt in range(max_retries):
            if auto_number or task_number is None:
                if legacy_id:
                    parsed = parse_task_number(legacy_id)
                    num = parsed if parsed is not None else self.get_next_task_number(project_id)
                else:
                    num = self.get_next_task_number(project_id)
            else:
                num = task_number

            lid = legacy_id if legacy_id is not None else f"T-{num:02d}"

            if task_uuid is None:
                actual_uuid = generate_task_uuid(project_id, lid)
            elif isinstance(task_uuid, str):
                actual_uuid = uuid.UUID(task_uuid)
            else:
                actual_uuid = task_uuid

            dep_uuid = uuid.UUID(str(depends_on_uuid)) if depends_on_uuid else None

            stmt = insert(tasks).values(
                task_uuid=actual_uuid,
                project_id=project_id,
                task_number=num,
                legacy_id=lid,
                title=title.strip(),
                mode=mode,
                status=status,
                version=1,
                steps_done=0,
                steps_total=max(1, steps_total),
                depends_on_uuid=dep_uuid,
                worktree=worktree,
                metadata=metadata or {},
            )

            has_nested = hasattr(self.session, "begin_nested")
            savepoint = self.session.begin_nested() if has_nested else None
            try:
                self.session.execute(stmt)
                return {
                    "task_uuid": str(actual_uuid),
                    "project_id": project_id,
                    "task_number": num,
                    "legacy_id": lid,
                    "title": title.strip(),
                    "mode": mode,
                    "status": status,
                    "version": 1,
                    "steps_done": 0,
                    "steps_total": max(1, steps_total),
                    "depends_on_uuid": str(dep_uuid) if dep_uuid else None,
                    "worktree": worktree,
                }
            except IntegrityError:
                if savepoint is not None:
                    savepoint.rollback()
                if auto_number and attempt < max_retries - 1:
                    continue
                raise

    def update_task(
        self,
        *,
        project_id: str,
        task_id: Union[uuid.UUID, str],
        expected_version: int,
        **updates: Any,
    ) -> dict[str, Any]:
        """Perform optimistic-locked update raising TaskMutationConflict on version mismatch."""
        target_uuid = None
        target_legacy = None
        try:
            target_uuid = uuid.UUID(str(task_id))
        except (ValueError, AttributeError):
            target_legacy = str(task_id)

        where_clause = tasks.c.project_id == project_id
        if target_uuid:
            where_clause = where_clause & ((tasks.c.task_uuid == target_uuid) | (tasks.c.legacy_id == str(task_id)))
        else:
            where_clause = where_clause & (tasks.c.legacy_id == target_legacy)

        # Attempt atomic optimistic update
        update_values = dict(updates)
        update_values["version"] = expected_version + 1
        update_values["updated_at"] = func.now()

        stmt = (
            update(tasks)
            .where(where_clause & (tasks.c.version == expected_version))
            .values(**update_values)
        )
        res = self.session.execute(stmt)
        rowcount = getattr(res, "rowcount", None)

        if rowcount == 0 or rowcount is None:
            # Check whether task exists or version mismatched
            check_stmt = select(tasks.c.version, tasks.c.legacy_id, tasks.c.task_uuid).where(where_clause)
            check_res = self.session.execute(check_stmt)
            row = None
            if hasattr(check_res, "mappings"):
                row = check_res.mappings().first()
            elif hasattr(check_res, "fetchone"):
                row = check_res.fetchone()

            if not row:
                raise KeyError(f"Task '{task_id}' not found in project '{project_id}'")

            try:
                current_ver = row["version"]
            except Exception:
                current_ver = row[0]

            if current_ver != expected_version:
                raise TaskMutationConflict(
                    f"Version conflict on task {task_id}: expected {expected_version}, current {current_ver}",
                    code="stale_task_version",
                )

        return self.get_task(project_id, task_id) or {"version": expected_version + 1}

    def get_task(self, project_id: str, task_id: Union[uuid.UUID, str]) -> Optional[dict[str, Any]]:
        """Retrieve a task by UUID or legacy ID within a project."""
        target_uuid = None
        target_legacy = None
        try:
            target_uuid = uuid.UUID(str(task_id))
        except (ValueError, AttributeError):
            target_legacy = str(task_id)

        where_clause = tasks.c.project_id == project_id
        if target_uuid:
            where_clause = where_clause & ((tasks.c.task_uuid == target_uuid) | (tasks.c.legacy_id == str(task_id)))
        else:
            where_clause = where_clause & (tasks.c.legacy_id == target_legacy)

        stmt = select(tasks).where(where_clause)
        res = self.session.execute(stmt)
        if hasattr(res, "mappings"):
            row = res.mappings().first()
            if row:
                d = dict(row)
                d["task_uuid"] = str(d["task_uuid"])
                if d.get("depends_on_uuid"):
                    d["depends_on_uuid"] = str(d["depends_on_uuid"])
                return d
        return None

    def list_tasks(
        self,
        project_id: str,
        *,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List tasks ordered by task_number with pagination."""
        stmt = (
            select(tasks)
            .where(tasks.c.project_id == project_id)
            .order_by(tasks.c.task_number.asc())
            .limit(max(1, limit))
            .offset(max(0, offset))
        )
        if status:
            stmt = stmt.where(tasks.c.status == status)

        res = self.session.execute(stmt)
        if hasattr(res, "mappings"):
            rows = res.mappings().all()
            output = []
            for row in rows:
                d = dict(row)
                d["task_uuid"] = str(d["task_uuid"])
                if d.get("depends_on_uuid"):
                    d["depends_on_uuid"] = str(d["depends_on_uuid"])
                output.append(d)
            return output
        return []


class SqlUnitOfWork:
    """Short-lived transactional unit of work context manager."""

    def __init__(self, session_factory: Callable[[], SessionLike]) -> None:
        self.session_factory = session_factory
        self.session: Optional[SessionLike] = None
        self.tasks: Optional[SqlTaskRepository] = None
        self.outbox: Optional[Any] = None

    def __enter__(self) -> "SqlUnitOfWork":
        self.session = self.session_factory()
        self.tasks = SqlTaskRepository(self.session)
        from .outbox import OutboxRepository
        self.outbox = OutboxRepository(self.session)
        return self

    def commit(self) -> None:
        if self.session:
            self.session.commit()

    def rollback(self) -> None:
        if self.session:
            self.session.rollback()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        if self.session is None:
            return False
        try:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
        finally:
            self.session.close()
        return False
