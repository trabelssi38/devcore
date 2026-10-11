"""
tasks.py -- DEV_CORE Task Service (Python Native)
Provides task creation, next task selection, stepping, and completion.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import json
import os
import sqlite3
import tempfile
from uuid import uuid4
from typing import Any, Dict, List, Optional


from devcore_engine.db import connect_db, get_data_root, get_db_path
from devcore_engine.context import RequestContext, validate_project_id
from devcore_engine.services.events import EventBus


def _validate_project_id(project_id: Optional[str]) -> str:
    return validate_project_id(project_id)


class StaleTaskVersion(ValueError):
    """The task changed after the caller read it."""


def _check_task_version(task: Dict[str, Any], expected_version: Optional[int]) -> None:
    if expected_version is None:
        return
    if type(expected_version) is not int or expected_version < 1:
        raise ValueError("expected_version must be a positive integer")
    if "version" not in task:
        raise ValueError("task version unavailable; migrate the database before conditional edits")
    if task["version"] != expected_version:
        raise StaleTaskVersion(
            f"stale task version: expected {expected_version}, current {task['version']}"
        )


class TaskService:
    def __init__(
        self,
        data_root: Optional[Path | sqlite3.Connection] = None,
    ):
        if isinstance(data_root, sqlite3.Connection):
            self.conn = data_root
            database_file = self.conn.execute("PRAGMA database_list").fetchone()[2]
            if database_file and Path(database_file).resolve() != get_db_path().resolve():
                self.data_root = Path(database_file).parent
            else:
                self.data_root = get_data_root()
        else:
            self.data_root = data_root or get_data_root()
            if data_root is not None:
                self.conn = connect_db(self.data_root / "devcore.db")
            else:
                self.conn = connect_db()
        self.event_bus = EventBus(self.conn)



    def export_legacy_json(self, project_id: str, export_root: Path) -> Path:
        """Explicit, atomic snapshot for legacy consumers; never part of a task mutation."""
        project_id = _validate_project_id(project_id)
        mem_dir = Path(export_root) / "Memory" / project_id
        tmp_path = None
        try:
            mem_dir.mkdir(parents=True, exist_ok=True)
            json_path = mem_dir / "tasks.json"
            board = self.get_board(project_id)
            tasks_list = []
            for t in board["tasks"]:
                meta = t.get("metadata", {})
                steps_list = []
                details_text = ""
                if isinstance(meta, str) and (meta.strip().startswith("[") or meta.strip().startswith("{")):
                    try:
                        meta = json.loads(meta)
                    except Exception:
                        meta = {}
                
                if isinstance(meta, list):
                    steps_list = meta
                elif isinstance(meta, dict):
                    details_text = meta.get("details", "")
                    steps_list = meta.get("steps", [])
                else:
                    details_text = str(meta or "")

                tasks_list.append({
                    "id": t["id"],
                    "title": t["title"],
                    "mode": t["mode"],
                    "status": t["status"],
                    "steps_total": t["steps_total"],
                    "steps_done": t["steps_done"],
                    "version": t.get("version"),
                    "depends_on": t.get("depends_on"),
                    "worktree": t.get("worktree", "main"),
                    "details": details_text,
                    "steps": steps_list,
                    "started_at": t.get("started_at") or "",
                    "completed_at": t.get("completed_at") or ""
                })
            obj = {
                "project": project_id,
                "current_task": board["current_task"],
                "tasks": tasks_list
            }
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=mem_dir, prefix=".tasks-", suffix=".tmp", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                json.dump(obj, tmp, indent=2, ensure_ascii=False)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_path, json_path)
            return json_path
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)

    def get_board(self, project_id: str) -> Dict[str, Any]:
        project_id = _validate_project_id(project_id)
        cursor = self.conn.cursor()
        rows = cursor.execute(
            "SELECT * FROM tasks WHERE project_id = ? AND status <> 'deleted' ORDER BY created_at ASC;",
            (project_id,),
        ).fetchall()

        tasks = [dict(r) for r in rows]
        active = next((t for t in tasks if t["status"] == "in_progress"), None)

        return {
            "project": project_id,
            "current_task": active["id"] if active else None,
            "tasks": tasks,
        }

    def get_task(self, task_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        project_id = _validate_project_id(project_id)
        cursor = self.conn.cursor()
        row = cursor.execute(
            "SELECT * FROM tasks WHERE id = ? AND project_id = ? AND status <> 'deleted';",
            (task_id, project_id),
        ).fetchone()
        return dict(row) if row else None

    def add_task(
        self,
        title: str,
        mode: str = "coding",
        steps: int = 1,
        project_id: Optional[str] = None,
        depends_on: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        project_id = _validate_project_id(project_id)

        cursor = self.conn.cursor()
        title_clean = title.strip().lower()

        # Serialize number allocation across connections sharing the SQLite database.
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            if idempotency_key:
                imported = cursor.execute(
                    "SELECT task_id FROM task_imports WHERE project_id = ? AND source_key = ?",
                    (project_id, idempotency_key),
                ).fetchone()
                if imported:
                    self.conn.commit()
                    existing = self.get_task(imported["task_id"], project_id)
                    if existing is None:
                        raise ValueError("import source refers to a deleted task")
                    return existing
            rows = cursor.execute(
                "SELECT id FROM tasks WHERE project_id = ? AND id LIKE 'T-%'", (project_id,)
            ).fetchall()
            max_num = 0
            for r in rows:
                tid = r[0]
                if tid and tid.startswith("T-") and not tid.startswith("T-GIT-"):
                    try:
                        max_num = max(max_num, int(tid.split("-")[1]))
                    except ValueError:
                        pass
            next_num = max_num + 1
            task_id = f"T-{next_num:02d}" if next_num < 100 else f"T-{next_num}"
            steps_total = max(1, steps)
            meta_json = json.dumps(metadata or {})

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
            if idempotency_key:
                self.conn.execute(
                    "INSERT INTO task_imports(project_id, source_key, task_id) VALUES (?, ?, ?)",
                    (project_id, idempotency_key, task_id),
                )
            self.event_bus.append_in_transaction(
                "TaskAdded",
                {"task_id": task_id, "title": title_clean, "mode": mode, "steps_total": steps_total},
                project=project_id,
                task_id=task_id,
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        return self.get_task(task_id, project_id)  # type: ignore

    def next_task(self, project_id: str) -> Optional[Dict[str, Any]]:
        project_id = _validate_project_id(project_id)
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            selected = self._select_next_task_in_transaction(project_id)
            self.conn.commit()
            return selected
        except Exception:
            self.conn.rollback()
            raise

    def _select_next_task_in_transaction(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Select on the caller's transaction, without committing an activation."""
        if not self.conn.in_transaction:
            raise RuntimeError("task selection requires an active transaction")
        cursor = self.conn.cursor()
        active = cursor.execute(
            "SELECT * FROM tasks WHERE project_id = ? AND status = 'in_progress' ORDER BY created_at ASC LIMIT 1;",
            (project_id,),
        ).fetchone()
        if active:
            return dict(active)
        candidates = cursor.execute(
            "SELECT * FROM tasks WHERE project_id = ? AND status = 'todo' ORDER BY created_at ASC;",
            (project_id,),
        ).fetchall()
        next_t = None
        for cand in candidates:
            candidate = dict(cand)
            dep_id = candidate.get("depends_on")
            if not dep_id or (
                (dep := self.get_task(dep_id, project_id)) and dep.get("status") == "done"
            ):
                next_t = candidate
                break
        if not next_t:
            return None
        t_id = next_t["id"]
        updated = self.conn.execute(
            "UPDATE tasks SET status = 'in_progress', "
            "started_at = COALESCE(started_at, datetime('now')), updated_at = datetime('now') "
            "WHERE id = ? AND project_id = ? AND status = 'todo'",
            (t_id, project_id),
        )
        if updated.rowcount != 1:
            raise RuntimeError("task selection changed during the transaction")
        self.event_bus.append_in_transaction(
            "TaskNext", {"task_id": t_id, "title": next_t["title"]},
            project=project_id, task_id=t_id,
        )
        return self.get_task(t_id, project_id)

    def _validate_actor_context(self, context: Optional[RequestContext], project_id: str) -> None:
        if context is not None and (context.project_id != project_id or context.user_id is None):
            raise ValueError("audit context requires a user and the matching project")

    def _audit_task_mutation(self, context: Optional[RequestContext], task: Dict[str, Any],
                             action: str) -> None:
        """Trusted adapters supply the actor; insert before committing the task write.

        Historical callers without context remain unaudited. This is not an ACL.
        Never serialize request bodies, task text or authentication secrets here.
        """
        if context is None:
            return
        after = self.conn.execute(
            "SELECT status, version FROM tasks WHERE id = ? AND project_id = ?",
            (task["id"], context.project_id),
        ).fetchone()
        details = {"schema_version": 1, "trace_id": context.trace_id,
                   "session_id": context.session_id,
                   "before": {"status": task["status"], "version": task["version"]},
                   "after": {"status": after["status"], "version": after["version"]}}
        self.conn.execute(
            "INSERT INTO audit_log(id,project_id,task_id,actor,action,entity_type,entity_id,details) "
            "VALUES (?,?,?,?,?,'task',?,?)",
            (str(uuid4()), context.project_id, task["id"], context.user_id,
             action, task["id"], json.dumps(details, separators=(",", ":"))),
        )

    def complete_task(self, task_id: Optional[str] = None, project_id: Optional[str] = None,
                      expected_version: Optional[int] = None, *,
                      context: Optional[RequestContext] = None) -> Optional[Dict[str, Any]]:
        project_id = _validate_project_id(project_id)
        self._validate_actor_context(context, project_id)
        if expected_version is not None and not task_id:
            raise ValueError("task_id is required with expected_version")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            if not task_id:
                active = self._select_next_task_in_transaction(project_id)
                if not active:
                    self.conn.rollback()
                    return None
                task_id = active["id"]
            task = self.get_task(task_id, project_id)
            if task is None or task["status"] == "deleted":
                self.conn.rollback()
                return None
            _check_task_version(task, expected_version)
            if task["status"] == "done":
                self.conn.commit()
                return task
            condition = " AND version = ?" if expected_version is not None else ""
            updated = self.conn.execute(
                "UPDATE tasks SET status = 'done', steps_done = steps_total, "
                "completed_at = datetime('now'), updated_at = datetime('now') "
                "WHERE id = ? AND project_id = ? AND status <> 'deleted'" + condition,
                (task_id, project_id) + ((expected_version,) if expected_version is not None else ()),
            )
            if updated.rowcount != 1:
                raise StaleTaskVersion("task changed during completion")
            self._audit_task_mutation(context, task, "task.complete")
            completed = self.get_task(task_id, project_id)
            self.event_bus.append_in_transaction(
                "TaskCompleted", {"task_id": task_id, "title": completed["title"]},
                project=project_id, task_id=task_id,
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        return completed

    def delete_task(self, task_id: str, project_id: str,
                    expected_version: Optional[int] = None, *,
                   context: Optional[RequestContext] = None) -> Optional[Dict[str, Any]]:
        """Hide a task while retaining its identity and referenced history."""
        project_id = _validate_project_id(project_id)
        self._validate_actor_context(context, project_id)
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            task = self.get_task(task_id, project_id)
            if task is None:
                self.conn.rollback()
                return None
            _check_task_version(task, expected_version)
            dependent = self.conn.execute(
                "SELECT id FROM tasks WHERE project_id = ? AND depends_on = ? "
                "AND status IN ('todo', 'in_progress') LIMIT 1",
                (project_id, task_id),
            ).fetchone()
            if dependent:
                raise ValueError(f"Task {task_id} is required by {dependent['id']}")
            condition = " AND version = ?" if expected_version is not None else ""
            updated = self.conn.execute(
                "UPDATE tasks SET status = 'deleted', updated_at = datetime('now') "
                "WHERE id = ? AND project_id = ? AND status <> 'deleted'" + condition,
                (task_id, project_id) + ((expected_version,) if expected_version is not None else ()),
            )
            if updated.rowcount != 1:
                raise StaleTaskVersion("task changed during deletion")
            self._audit_task_mutation(context, task, "task.delete")
            self.event_bus.append_in_transaction(
                "TaskDeleted", {"task_id": task_id, "previous_status": task["status"]},
                project=project_id, task_id=task_id,
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        return task

    def step_task(self, task_id: Optional[str] = None, step_number: Optional[int] = None,
                  project_id: Optional[str] = None, expected_version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        project_id = _validate_project_id(project_id)
        if step_number is not None and (type(step_number) is not int or step_number < 1):
            raise ValueError("step_number must be a positive integer")
        if expected_version is not None and not task_id:
            raise ValueError("task_id is required with expected_version")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            if not task_id:
                active = self._select_next_task_in_transaction(project_id)
                if not active:
                    self.conn.rollback()
                    return None
                task_id = active["id"]
            t = self.get_task(task_id, project_id)
            if not t:
                self.conn.rollback()
                return None
            _check_task_version(t, expected_version)
            if t["status"] == "done":
                self.conn.commit()
                return t
            if t["status"] not in {"todo", "in_progress"}:
                raise ValueError("task must be todo or in_progress before stepping")
            new_done = min(
                t["steps_total"],
                t["steps_done"] + 1 if step_number is None else max(t["steps_done"], step_number),
            )
            if new_done == t["steps_done"]:
                self.conn.commit()
                return t
            dependency_id = t.get("depends_on")
            if dependency_id:
                dependency = self.get_task(dependency_id, project_id)
                if dependency is None or dependency["status"] != "done":
                    raise ValueError("task dependency must be completed in the same project before stepping")
            new_status = "done" if new_done >= t["steps_total"] else "in_progress"
            if new_status == "in_progress":
                active = self.conn.execute(
                    "SELECT id FROM tasks WHERE project_id = ? AND status = 'in_progress' "
                    "AND id <> ? LIMIT 1", (project_id, task_id),
                ).fetchone()
                if active:
                    raise ValueError(f"task {active['id']} is already active")

            condition = " AND version = ?" if expected_version is not None else ""
            updated = self.conn.execute(
                """
                UPDATE tasks
                SET steps_done = ?, status = ?, completed_at = CASE WHEN ? = 'done' THEN COALESCE(completed_at, datetime('now')) ELSE completed_at END, updated_at = datetime('now')
                WHERE id = ? AND project_id = ? AND status <> 'deleted'
                """ + condition,
                (new_done, new_status, new_status, task_id, project_id)
                + ((expected_version,) if expected_version is not None else ()),
            )
            if updated.rowcount != 1:
                raise StaleTaskVersion("task changed during step")
            self.event_bus.append_in_transaction(
                "TaskStepDone", {"task_id": task_id, "steps_done": new_done, "steps_total": t["steps_total"]},
                project=project_id, task_id=task_id,
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        return self.get_task(task_id, project_id)

    def edit_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        mode: Optional[str] = None,
        steps_total: Optional[int] = None,
        project_id: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        project_id = _validate_project_id(project_id)
        if not any(value is not None for value in (title, mode, steps_total)):
            raise ValueError("at least one edit field is required")
        if title is not None and not title.strip():
            raise ValueError("title must not be empty")
        if mode is not None and mode not in {"coding", "reasoning", "bulk"}:
            raise ValueError("invalid mode")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            task = self.get_task(task_id, project_id)
            if not task:
                self.conn.rollback()
                return None
            _check_task_version(task, expected_version)
            new_steps = steps_total if steps_total is not None else task["steps_total"]
            if new_steps < 1 or new_steps < task["steps_done"]:
                raise ValueError("steps_total must be positive and at least steps_done")
            if task["status"] == "done" and new_steps != task["steps_done"]:
                raise ValueError("a completed task must retain its completed step count")
            condition = " AND version = ?" if expected_version is not None else ""
            params = (title.strip() if title is not None else task["title"], mode or task["mode"],
                      new_steps, task_id, project_id)
            updated = self.conn.execute(
                "UPDATE tasks SET title = ?, mode = ?, steps_total = ?, updated_at = datetime('now') "
                "WHERE id = ? AND project_id = ? AND status <> 'deleted'" + condition,
                params + ((expected_version,) if expected_version is not None else ()),
            )
            if updated.rowcount != 1:
                raise StaleTaskVersion("task changed during the edit")
            self.event_bus.append_in_transaction("TaskEdited", {"task_id": task_id}, project=project_id, task_id=task_id)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return self.get_task(task_id, project_id)

    def pause_task(self, task_id: Optional[str] = None, project_id: Optional[str] = None,
                   expected_version: Optional[int] = None, *,
                   context: Optional[RequestContext] = None) -> Optional[Dict[str, Any]]:
        project_id = _validate_project_id(project_id)
        self._validate_actor_context(context, project_id)
        if expected_version is not None and not task_id:
            raise ValueError("task_id is required with expected_version")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            if not task_id:
                row = self.conn.execute(
                    "SELECT id FROM tasks WHERE project_id = ? AND status = 'in_progress' "
                    "ORDER BY started_at, id LIMIT 1", (project_id,),
                ).fetchone()
                task_id = row["id"] if row else None
            if task_id and (task := self.get_task(task_id, project_id)):
                _check_task_version(task, expected_version)
            condition = " AND version = ?" if expected_version is not None else ""
            updated = self.conn.execute(
                "UPDATE tasks SET status = 'paused', updated_at = datetime('now') "
                "WHERE id = ? AND project_id = ? AND status = 'in_progress'" + condition,
                (task_id, project_id) + ((expected_version,) if expected_version is not None else ()),
            ) if task_id else None
            if updated and updated.rowcount == 1:
                self._audit_task_mutation(context, task, "task.pause")
                self.event_bus.append_in_transaction("TaskPaused", {"task_id": task_id}, project=project_id, task_id=task_id)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        if not updated or updated.rowcount == 0:
            return None
        return self.get_task(task_id, project_id)

    def skip_task(self, task_id: Optional[str] = None, reason: str = "", project_id: Optional[str] = None,
                  expected_version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        project_id = _validate_project_id(project_id)
        if expected_version is not None and not task_id:
            raise ValueError("task_id is required with expected_version")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            if not task_id:
                row = self.conn.execute(
                    "SELECT id FROM tasks WHERE project_id = ? AND status = 'in_progress' "
                    "ORDER BY started_at, id LIMIT 1", (project_id,),
                ).fetchone()
                task_id = row["id"] if row else None
            if task_id and (task := self.get_task(task_id, project_id)):
                _check_task_version(task, expected_version)
            condition = " AND version = ?" if expected_version is not None else ""
            updated = self.conn.execute(
                "UPDATE tasks SET status = 'skipped', updated_at = datetime('now') "
                "WHERE id = ? AND project_id = ? AND status = 'in_progress'" + condition,
                (task_id, project_id) + ((expected_version,) if expected_version is not None else ()),
            ) if task_id else None
            if updated and updated.rowcount == 1:
                self.event_bus.append_in_transaction("TaskSkipped", {"task_id": task_id, "reason": reason}, project=project_id, task_id=task_id)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        if not updated or updated.rowcount == 0:
            return None
        return self.get_task(task_id, project_id)

    def resume_task(self, task_id: Optional[str] = None, project_id: Optional[str] = None,
                    expected_version: Optional[int] = None, *,
                   context: Optional[RequestContext] = None) -> Optional[Dict[str, Any]]:
        project_id = _validate_project_id(project_id)
        self._validate_actor_context(context, project_id)
        if expected_version is not None and not task_id:
            raise ValueError("task_id is required with expected_version")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            active = self.conn.execute(
                "SELECT id FROM tasks WHERE project_id = ? AND status = 'in_progress' LIMIT 1",
                (project_id,),
            ).fetchone()
            if active:
                raise ValueError(f"task {active['id']} is already active")
            if not task_id:
                paused = self.conn.execute(
                    "SELECT id FROM tasks WHERE project_id = ? AND status = 'paused' "
                    "ORDER BY updated_at, id LIMIT 1", (project_id,),
                ).fetchone()
                task_id = paused["id"] if paused else None
            if task_id and (task := self.get_task(task_id, project_id)):
                _check_task_version(task, expected_version)
                if task["status"] == "paused" and task.get("depends_on"):
                    dependency = self.get_task(task["depends_on"], project_id)
                    if dependency is None or dependency["status"] != "done":
                        raise ValueError("task dependency must be completed in the same project before resuming")
            condition = " AND version = ?" if expected_version is not None else ""
            updated = self.conn.execute(
                "UPDATE tasks SET status = 'in_progress', updated_at = datetime('now') "
                "WHERE id = ? AND project_id = ? AND status = 'paused'" + condition,
                (task_id, project_id) + ((expected_version,) if expected_version is not None else ()),
            ) if task_id else None
            if updated and updated.rowcount == 1:
                self._audit_task_mutation(context, task, "task.resume")
                self.event_bus.append_in_transaction("TaskResumed", {"task_id": task_id}, project=project_id, task_id=task_id)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        if not updated or updated.rowcount == 0:
            return None
        return self.get_task(task_id, project_id)


if __name__ == "__main__":
    ts = TaskService()
    board = ts.get_board("devcore")
    print(f"[TaskService] Total tasks for devcore: {len(board['tasks'])}")
    active = ts.next_task("devcore")
    print(f"[TaskService] Active task: {active['id'] if active else 'None'}")
