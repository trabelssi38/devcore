from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Protocol

from sqlalchemy import insert, select

from devcore_api.contracts import TaskContract

from .models import tasks


class SessionLike(Protocol):
    def execute(self, statement: Any) -> Any: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...


class SqlTaskRepository:
    def __init__(self, session: SessionLike):
        self.session = session

    def list_tasks(self, project: str) -> list[TaskContract]:
        statement = (
            select(
                tasks.c.id,
                tasks.c.title,
                tasks.c.status,
                tasks.c.mode,
                tasks.c.steps_done,
                tasks.c.steps_total,
                tasks.c.depends_on,
                tasks.c.worktree,
            )
            .where(tasks.c.project_id == project)
            .order_by(tasks.c.created_at.asc(), tasks.c.id.asc())
        )
        rows: Iterable[dict[str, Any]] = self.session.execute(statement).mappings().all()
        return [TaskContract(**dict(row)) for row in rows]

    def create_task(
        self,
        *,
        project_id: str,
        task_id: str,
        title: str,
        mode: str = "coding",
        status: str = "todo",
        steps_total: int = 1,
        worktree: str = "main",
    ) -> None:
        statement = insert(tasks).values(
            id=task_id,
            project_id=project_id,
            title=title,
            mode=mode,
            status=status,
            steps_done=0,
            steps_total=steps_total,
            worktree=worktree,
        )
        self.session.execute(statement)


class UnitOfWork:
    def __init__(self, session_factory: Callable[[], SessionLike]):
        self.session_factory = session_factory
        self.session: SessionLike | None = None

    def __enter__(self) -> "UnitOfWork":
        self.session = self.session_factory()
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
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
