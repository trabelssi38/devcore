"""
tasks.py -- DEV_CORE Task Service (Python Native)
Replaces task_service.ps1 by executing task CRUD and state transitions directly in devcore.db.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import json
import sqlite3
import uuid
from typing import Any, Dict, List, Optional

from devcore_engine.db import connect_db, init_db
from devcore_engine.services.events import EventBus


class TaskService:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or init_db()
        self.event_bus = EventBus(self.conn)

    def get_board(self, project_id: str = "devcore") -> Dict[str, Any]:
        cursor = self.conn.cursor()
        rows = cursor.execute(
            """
            SELECT * FROM tasks
            WHERE project_id = ?
            ORDER BY created_at ASC;
            """,
            (project_id,),
        ).fetchall()

        tasks = []
        current_task_id = None
        for r in rows:
            t = dict(r)
            try:
                t["metadata"] = json.loads(t["metadata"])
            except Exception:
                pass
            if t["status"] == "in_progress" and not current_task_id:
                current_task_id = t["id"]
            tasks.append(t)

        return {
            "project": project_id,
            "current_task": current_task_id,
            "tasks": tasks,
        }

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        row = cursor.execute("SELECT * FROM tasks WHERE id = ?;", (task_id,)).fetchone()
        if not row:
            return None
        t = dict(row)
        try:
            t["metadata"] = json.loads(t["metadata"])
        except Exception:
            pass
        return t

    def add_task(
        self,
        title: str,
        mode: str = "coding",
        depends_on: Optional[str] = None,
        steps: int = 1,
        project_id: str = "devcore",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Generate next task ID (e.g. T-15, T-16 or UUID)
        cursor = self.conn.cursor()
        max_t = cursor.execute(
            "SELECT id FROM tasks WHERE project_id = ? AND id LIKE 'T-%' ORDER BY ROWID DESC LIMIT 1;",
            (project_id,),
        ).fetchone()

        next_num = 1
        if max_t:
            try:
                next_num = int(max_t["id"].split("-")[1]) + 1
            except Exception:
                next_num = 1

        task_id = f"T-{next_num:02d}"
        steps_total = max(1, steps)
        meta_json = json.dumps(metadata or {})

        # Ensure project row exists
        self.conn.execute(
            """
            INSERT INTO projects (id, name, root_path, status)
            VALUES (?, ?, 'C:/devcore', 'active')
            ON CONFLICT(id) DO NOTHING;
            """,
            (project_id, project_id),
        )

        self.conn.execute(
            """
            INSERT INTO tasks (id, project_id, title, mode, status, steps_done, steps_total, depends_on, metadata)
            VALUES (?, ?, ?, ?, 'todo', 0, ?, ?, ?);
            """,
            (task_id, project_id, title, mode, steps_total, depends_on, meta_json),
        )

        self.conn.commit()

        self.event_bus.publish(
            "TaskAdded",
            {"task_id": task_id, "title": title, "mode": mode, "steps_total": steps_total},
            project=project_id,
            task_id=task_id,
        )

        return self.get_task(task_id)  # type: ignore

    def next_task(self, project_id: str = "devcore") -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        
        # 1. Check if there is already an in_progress task
        active = cursor.execute(
            "SELECT * FROM tasks WHERE project_id = ? AND status = 'in_progress' ORDER BY created_at ASC LIMIT 1;",
            (project_id,),
        ).fetchone()

        if active:
            return dict(active)

        # 2. Pick next todo task whose dependencies are satisfied
        candidates = cursor.execute(
            "SELECT * FROM tasks WHERE project_id = ? AND status = 'todo' ORDER BY created_at ASC;",
            (project_id,),
        ).fetchall()

        next_t = None
        for cand in candidates:
            dep_id = cand["depends_on"]
            if not dep_id:
                next_t = cand
                break
            # Verify dependency is done
            dep = cursor.execute("SELECT status FROM tasks WHERE id = ?;", (dep_id,)).fetchone()
            if dep and dep["status"] == "done":
                next_t = cand
                break

        if not next_t:
            return None

        t_id = next_t["id"]
        self.conn.execute(
            """
            UPDATE tasks
            SET status = 'in_progress', started_at = COALESCE(started_at, datetime('now')), updated_at = datetime('now')
            WHERE id = ?;
            """,
            (t_id,),
        )
        self.conn.commit()

        self.event_bus.publish("TaskNext", {"task_id": t_id, "title": next_t["title"]}, project=project_id, task_id=t_id)
        return self.get_task(t_id)

    def complete_task(self, task_id: Optional[str] = None, project_id: str = "devcore") -> Optional[Dict[str, Any]]:
        if not task_id:
            active = self.next_task(project_id)
            if not active:
                return None
            task_id = active["id"]

        self.conn.execute(
            """
            UPDATE tasks
            SET status = 'done', steps_done = steps_total, completed_at = datetime('now'), updated_at = datetime('now')
            WHERE id = ?;
            """,
            (task_id,),
        )
        self.conn.commit()

        completed = self.get_task(task_id)
        if completed:
            self.event_bus.publish("TaskCompleted", {"task_id": task_id, "title": completed["title"]}, project=project_id, task_id=task_id)
        return completed

    def step_task(self, task_id: Optional[str] = None, step_number: Optional[int] = None, project_id: str = "devcore") -> Optional[Dict[str, Any]]:
        if not task_id:
            active = self.next_task(project_id)
            if not active:
                return None
            task_id = active["id"]

        t = self.get_task(task_id)
        if not t:
            return None

        new_done = (step_number if step_number is not None else t["steps_done"] + 1)
        new_done = min(new_done, t["steps_total"])
        new_status = "done" if new_done >= t["steps_total"] else "in_progress"

        self.conn.execute(
            """
            UPDATE tasks
            SET steps_done = ?, status = ?, updated_at = datetime('now')
            WHERE id = ?;
            """,
            (new_done, new_status, task_id),
        )
        self.conn.commit()

        self.event_bus.publish("TaskStepDone", {"task_id": task_id, "steps_done": new_done, "steps_total": t["steps_total"]}, project=project_id, task_id=task_id)
        return self.get_task(task_id)


if __name__ == "__main__":
    ts = TaskService()
    board = ts.get_board("devcore")
    print(f"[TaskService] Total tasks for devcore: {len(board['tasks'])}")
    active = ts.next_task("devcore")
    print(f"[TaskService] Active task: {active['id'] if active else 'None'}")
