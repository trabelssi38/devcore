"""
session.py -- DEV_CORE Session Lifecycle (Python Native)
Replaces session_start.ps1 and session_end.ps1 by handling session initialization and cleanup.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import os
import sqlite3
from typing import Any, Dict, Optional

from devcore_engine.context import RequestContext, project_from_directory, validate_project_id
from devcore_engine.db import connect_db, init_db
from devcore_engine.services.events import EventBus
from devcore_engine.services.tasks import TaskService


class SessionManager:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or init_db()
        self.event_bus = EventBus(self.conn)
        self.task_service = TaskService(self.conn)
        self._active_project: Optional[str] = None

    def get_active_project(self) -> str:
        if self._active_project:
            return self._active_project

        # Environment variable is scoped to this process, rather than all clients.
        env_proj = os.getenv("DEVCORE_ACTIVE_PROJECT_NAME")
        if env_proj:
            return validate_project_id(env_proj.strip())

        dir_proj = project_from_directory()
        if dir_proj:
            return dir_proj

        raise ValueError("No active project context found")

    def set_active_project(self, project_id: str) -> None:
        self._active_project = validate_project_id(project_id)

    def start_session(self, project_id: str | RequestContext) -> Dict[str, Any]:
        context = project_id if isinstance(project_id, RequestContext) else RequestContext(project_id=project_id)
        current_project = context.project_id

        # Ensure there is an active task, or create a default session task if none exists
        active_task = self.task_service.next_task(current_project)
        if not active_task:
            import datetime
            today = datetime.date.today().strftime("%Y-%m-%d")
            active_task = self.task_service.add_task(
                f"Session de travail auto ({today})",
                mode="coding",
                steps=1,
                project_id=current_project,
            )

        evt_id = self.event_bus.publish(
            "SessionStarted",
            {
                "project": current_project,
                "active_task": active_task["id"] if active_task else None,
            },
            project=current_project,
            task_id=active_task["id"] if active_task else None,
            correlation_id=context.trace_id,
        )

        return {
            "status": "started",
            "project": current_project,
            "active_task": active_task,
            "event_id": evt_id,
            "trace_id": context.trace_id,
        }

    def end_session(self, project_id: str | RequestContext) -> Dict[str, Any]:
        context = project_id if isinstance(project_id, RequestContext) else RequestContext(project_id=project_id)
        current_project = context.project_id
        
        evt_id = self.event_bus.publish(
            "SessionEnded",
            {"project": current_project},
            project=current_project,
            correlation_id=context.trace_id,
        )

        return {
            "status": "ended",
            "project": current_project,
            "event_id": evt_id,
            "trace_id": context.trace_id,
        }


if __name__ == "__main__":
    sm = SessionManager()
    start_info = sm.start_session("devcore")
    print(f"[SessionManager] Session started: {start_info}")
    end_info = sm.end_session("devcore")
    print(f"[SessionManager] Session ended: {end_info}")
