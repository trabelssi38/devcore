"""
tasks.py -- DEV_CORE Task Service (Python Native)
Provides task creation, next task selection, stepping, and completion.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import json
import sqlite3
from typing import Any, Dict, List, Optional


from devcore_engine.db import connect_db, get_data_root
from devcore_engine.services.events import EventBus


class TaskService:
    def __init__(self, data_root: Optional[Path | sqlite3.Connection] = None):
        if isinstance(data_root, sqlite3.Connection):
            self.conn = data_root
            self.data_root = get_data_root()
        else:
            self.data_root = data_root or get_data_root()
            self.conn = connect_db(self.data_root / "devcore.db")
        self.event_bus = EventBus(self.conn)



    def _sync_to_legacy_json(self, project_id: str = "devcore") -> None:
        try:
            mem_dir = self.data_root / "Memory" / project_id
            mem_dir.mkdir(parents=True, exist_ok=True)
            json_path = mem_dir / "tasks.json"
            board = self.get_board(project_id)
            tasks_list = []
            for t in board["tasks"]:
                meta = t.get("metadata", {})
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except Exception:
                        meta = {}
                tasks_list.append({
                    "id": t["id"],
                    "title": t["title"],
                    "mode": t["mode"],
                    "status": t["status"],
                    "steps_total": t["steps_total"],
                    "steps_done": t["steps_done"],
                    "depends_on": t.get("depends_on"),
                    "worktree": t.get("worktree", "main"),
                    "details": meta.get("details", "") if isinstance(meta, dict) else "",
                    "started_at": t.get("started_at") or "",
                    "completed_at": t.get("completed_at") or ""
                })
            obj = {
                "project": project_id,
                "current_task": board["current_task"],
                "tasks": tasks_list
            }
            json_path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def get_board(self, project_id: str = "devcore") -> Dict[str, Any]:
        cursor = self.conn.cursor()
        rows = cursor.execute(
            "SELECT * FROM tasks WHERE project_id = ? ORDER BY created_at ASC;",
            (project_id,),
        ).fetchall()

        tasks = [dict(r) for r in rows]
        active = next((t for t in tasks if t["status"] == "in_progress"), None)

        return {
            "project": project_id,
            "current_task": active["id"] if active else None,
            "tasks": tasks,
        }

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        row = cursor.execute("SELECT * FROM tasks WHERE id = ?;", (task_id,)).fetchone()
        return dict(row) if row else None

    def add_task(
        self,
        title: str,
        mode: str = "coding",
        steps: int = 1,
        project_id: str = "devcore",
        depends_on: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        title_clean = title.strip().lower()

        # Compute next task ID (e.g. T-01, T-02)
        max_t = cursor.execute(
            "SELECT id FROM tasks WHERE project_id = ? AND id LIKE 'T-%' ORDER BY CAST(SUBSTR(id, 3) AS INTEGER) DESC LIMIT 1;",
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
            (task_id, project_id, title_clean, mode, steps_total, depends_on, meta_json),
        )

        self.conn.commit()

        self.event_bus.publish(
            "TaskAdded",
            {"task_id": task_id, "title": title_clean, "mode": mode, "steps_total": steps_total},
            project=project_id,
            task_id=task_id,
        )

        self._sync_to_legacy_json(project_id)
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
            cand_dict = dict(cand)
            dep_id = cand_dict.get("depends_on")
            if not dep_id:
                next_t = cand_dict
                break
            
            dep = self.get_task(dep_id)
            if dep and dep.get("status") == "done":
                next_t = cand_dict
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
        self._sync_to_legacy_json(project_id)
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
        self._sync_to_legacy_json(project_id)
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
            SET steps_done = ?, status = ?, completed_at = CASE WHEN ? = 'done' THEN datetime('now') ELSE completed_at END, updated_at = datetime('now')
            WHERE id = ?;
            """,
            (new_done, new_status, new_status, task_id),
        )
        self.conn.commit()

        self.event_bus.publish("TaskStepDone", {"task_id": task_id, "steps_done": new_done, "steps_total": t["steps_total"]}, project=project_id, task_id=task_id)
        self._sync_to_legacy_json(project_id)
        return self.get_task(task_id)

    def edit_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        mode: Optional[str] = None,
        steps_total: Optional[int] = None,
        project_id: str = "devcore",
    ) -> Optional[Dict[str, Any]]:
        t = self.get_task(task_id)
        if not t:
            return None
        new_title = title if title is not None else t["title"]
        new_mode = mode if mode is not None else t["mode"]
        new_steps = steps_total if steps_total is not None else t["steps_total"]
        self.conn.execute(
            """
            UPDATE tasks
            SET title = ?, mode = ?, steps_total = ?, updated_at = datetime('now')
            WHERE id = ?;
            """,
            (new_title, new_mode, new_steps, task_id),
        )
        self.conn.commit()
        self._sync_to_legacy_json(project_id)
        return self.get_task(task_id)


if __name__ == "__main__":
    ts = TaskService()
    board = ts.get_board("devcore")
    print(f"[TaskService] Total tasks for devcore: {len(board['tasks'])}")
    active = ts.next_task("devcore")
    print(f"[TaskService] Active task: {active['id'] if active else 'None'}")
