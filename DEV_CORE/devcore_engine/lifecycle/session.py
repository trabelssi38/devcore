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

from devcore_engine.db import connect_db, init_db
from devcore_engine.services.events import EventBus
from devcore_engine.services.tasks import TaskService


class SessionManager:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or init_db()
        self.event_bus = EventBus(self.conn)
        self.task_service = TaskService(self.conn)

    def get_active_project(self) -> str:
        # 1. Environment variable check
        env_proj = os.getenv("DEVCORE_ACTIVE_PROJECT_NAME")
        if env_proj:
            return env_proj.strip()

        # 2. Runtime state check in devcore.db
        cursor = self.conn.cursor()
        row = cursor.execute("SELECT value FROM runtime_state WHERE key = 'active_project';").fetchone()
        if row and row["value"]:
            return row["value"].strip()

        # 3. Fallback to default project
        return "devcore"

    def set_active_project(self, project_id: str) -> None:
        self.conn.execute(
            """
            INSERT INTO runtime_state (key, value, updated_at)
            VALUES ('active_project', ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = datetime('now');
            """,
            (project_id.strip(),),
        )
        self.conn.commit()

    def start_session(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        current_project = project_id or self.get_active_project()
        self.set_active_project(current_project)

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
        )

        return {
            "status": "started",
            "project": current_project,
            "active_task": active_task,
            "event_id": evt_id,
        }

    def end_session(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        current_project = project_id or self.get_active_project()
        
        evt_id = self.event_bus.publish(
            "SessionEnded",
            {"project": current_project},
            project=current_project,
        )

        return {
            "status": "ended",
            "project": current_project,
            "event_id": evt_id,
        }


if __name__ == "__main__":
    sm = SessionManager()
    start_info = sm.start_session("devcore")
    print(f"[SessionManager] Session started: {start_info}")
    end_info = sm.end_session("devcore")
    print(f"[SessionManager] Session ended: {end_info}")
