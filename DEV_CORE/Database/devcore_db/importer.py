from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import insert

from .models import organizations, projects, tasks, users, workspace_memberships, workspaces


VALID_TASK_STATUS = {"todo", "active", "paused", "done", "skipped"}
VALID_TASK_MODE = {"reasoning", "coding", "bulk"}


@dataclass
class ReconciliationReport:
    project: str
    source_path: str
    tasks_seen: int = 0
    tasks_imported: int = 0
    tasks_skipped: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "ok" if not self.warnings else "partial"

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "project": self.project,
            "source_path": self.source_path,
            "tasks_seen": self.tasks_seen,
            "tasks_imported": self.tasks_imported,
            "tasks_skipped": self.tasks_skipped,
            "warnings": self.warnings,
        }


class TaskBoardImporter:
    def __init__(self, session):
        self.session = session

    def import_file(self, board_path: str | Path, *, root_path: str) -> ReconciliationReport:
        path = Path(board_path)
        board = json.loads(path.read_text(encoding="utf-8"))
        project_id = str(board.get("project") or "devcore")
        raw_tasks = list(board.get("tasks") or [])
        report = ReconciliationReport(project=project_id, source_path=str(path), tasks_seen=len(raw_tasks))
        organization_id = "org_default"
        workspace_id = f"wks_{project_id}"

        self.session.execute(
            insert(organizations).values(
                id=organization_id,
                name="Default Organization",
                status="active",
                metadata={"source": "tasks_json_import"},
            )
        )
        self.session.execute(
            insert(users).values(
                id="usr_system",
                email="system@devcore.local",
                display_name="System",
                status="active",
                metadata={"source": "tasks_json_import"},
            )
        )
        self.session.execute(
            insert(workspaces).values(
                id=workspace_id,
                organization_id=organization_id,
                name=project_id,
                status="active",
                metadata={"source": "tasks_json_import"},
            )
        )
        self.session.execute(
            insert(workspace_memberships).values(
                id=f"mem_{project_id}_system",
                workspace_id=workspace_id,
                user_id="usr_system",
                role="owner",
                metadata={"source": "tasks_json_import"},
            )
        )

        self.session.execute(
            insert(projects).values(
                id=project_id,
                workspace_id=workspace_id,
                name=project_id,
                root_path=root_path,
                status="active",
                metadata={"source": "tasks_json_import"},
            )
        )

        for index, raw_task in enumerate(raw_tasks):
            normalized, warning = self._normalize_task(raw_task, project_id=project_id, index=index)
            if warning:
                report.tasks_skipped += 1
                report.warnings.append(warning)
                continue
            self.session.execute(insert(tasks).values(**normalized))
            report.tasks_imported += 1

        return report

    def _normalize_task(self, raw_task: dict[str, Any], *, project_id: str, index: int) -> tuple[dict[str, Any], str | None]:
        task_id = str(raw_task.get("id") or "").strip()
        title = str(raw_task.get("title") or "").strip()
        status = str(raw_task.get("status") or "todo").strip()
        mode = str(raw_task.get("mode") or "coding").strip()

        if not task_id:
            return {}, f"task[{index}] skipped: missing id"
        if not title:
            return {}, f"task[{task_id}] skipped: missing title"
        if status not in VALID_TASK_STATUS:
            return {}, f"task[{task_id}] skipped: invalid status {status}"
        if mode not in VALID_TASK_MODE:
            return {}, f"task[{task_id}] skipped: invalid mode {mode}"

        steps_total = max(int(raw_task.get("steps_total") or 1), 1)
        steps_done = min(max(int(raw_task.get("steps_done") or 0), 0), steps_total)

        return {
            "id": task_id,
            "project_id": project_id,
            "title": title,
            "mode": mode,
            "status": status,
            "steps_done": steps_done,
            "steps_total": steps_total,
            "depends_on": raw_task.get("depends_on"),
            "worktree": raw_task.get("worktree") or "main",
            "metadata": {
                "source": raw_task.get("source") or "tasks_json",
                "details": raw_task.get("details"),
                "commit_hash": raw_task.get("commit_hash"),
            },
        }, None
