"""Transactional, project-scoped task transitions for the team profile."""

from __future__ import annotations

from contextlib import contextmanager
import json
from urllib.parse import unquote, urlparse
from uuid import uuid4

from devcore_engine.context import RequestContext
from devcore_engine.services.task_mutations import TaskMutationConflict, validate_safe_id


class PostgresTaskMutations:
    def __init__(self, dsn: str):
        parsed = urlparse(dsn.replace("postgresql+pg8000://", "postgresql://", 1))
        if parsed.scheme != "postgresql" or parsed.hostname not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("Task mutations require a local PostgreSQL DSN")
        if not parsed.username or not parsed.path or parsed.path == "/":
            raise ValueError("Task mutations require a PostgreSQL role and database")
        self._options = dict(
            user=unquote(parsed.username), password=unquote(parsed.password or ""),
            host=parsed.hostname, port=parsed.port or 5432,
            database=parsed.path.lstrip("/"),
        )

    @contextmanager
    def _transaction(self, project: str):
        project = validate_safe_id(project, "project")
        import pg8000.dbapi

        connection = pg8000.dbapi.connect(**self._options)
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT set_config('app.current_project_id', %s, true)", (project,))
            yield cursor
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _principal(project: str, context: RequestContext | None) -> str:
        if context is None or context.project_id != project or not context.user_id:
            raise TaskMutationConflict("Project mutation principal required", "project_access_denied")
        return context.user_id

    def transition(
        self, project: str, task_id: str, action: str, expected_version: int | None,
        context: RequestContext | None,
    ) -> tuple[bool, str]:
        project = validate_safe_id(project, "project")
        task_id = validate_safe_id(task_id, "task id")
        actor = self._principal(project, context)
        targets = {"complete": "done", "delete": "deleted", "pause": "paused", "resume": "in_progress"}
        if action not in targets:
            raise ValueError("Invalid task transition")
        if type(expected_version) is not int or expected_version < 1:
            raise TaskMutationConflict("Task version required", "task_version_required")

        with self._transaction(project) as cursor:
            # Serialize transitions that depend on the active task or its dependencies.
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (project,))
            cursor.execute("""SELECT task_uuid, legacy_id, status, version, depends_on_uuid
                FROM tasks WHERE project_id=%s AND (legacy_id=%s OR task_uuid::text=%s)
                FOR UPDATE""", (project, task_id, task_id))
            rows = cursor.fetchall()
            if len(rows) > 1:
                raise TaskMutationConflict("Ambiguous task identifier", "ambiguous_task_identifier")
            if not rows or rows[0][2] == "deleted":
                return False, f"Task {task_id} not found in project {project}"
            task_uuid, legacy_id, before, version, dependency_uuid = rows[0]
            if expected_version != version:
                raise TaskMutationConflict("Task version conflict", "stale_task_version")
            if action == "complete" and before == "done":
                return True, "Task already completed"
            required = {"pause": "in_progress", "resume": "paused"}
            if action in required and before != required[action]:
                raise TaskMutationConflict("Task transition is not valid", "invalid_transition")
            if action == "delete":
                cursor.execute("""SELECT legacy_id FROM tasks WHERE project_id=%s
                    AND depends_on_uuid=%s AND status IN ('todo','in_progress') LIMIT 1""",
                    (project, task_uuid))
                dependent = cursor.fetchone()
                if dependent:
                    raise TaskMutationConflict(
                        f"Task {task_id} is required by {dependent[0]}", "task_dependency_conflict"
                    )
            if action == "resume":
                cursor.execute("""SELECT 1 FROM tasks WHERE project_id=%s
                    AND status='in_progress' LIMIT 1""", (project,))
                if cursor.fetchone():
                    raise TaskMutationConflict("Project already has an active task", "task_transition_conflict")
                if dependency_uuid:
                    cursor.execute("""SELECT status FROM tasks WHERE project_id=%s
                        AND task_uuid=%s""", (project, dependency_uuid))
                    dependency = cursor.fetchone()
                    if dependency is None or dependency[0] != "done":
                        raise TaskMutationConflict("Task dependency incomplete", "task_transition_conflict")
            target = targets[action]
            new_version = version + 1
            cursor.execute("""UPDATE tasks SET status=%s, version=%s,
                steps_done=CASE WHEN %s='done' THEN steps_total ELSE steps_done END,
                completed_at=CASE WHEN %s='done' THEN now() ELSE completed_at END,
                updated_at=now() WHERE task_uuid=%s AND project_id=%s""",
                (target, new_version, target, target, task_uuid, project))
            entity_id = legacy_id or str(task_uuid)
            details = json.dumps({"schema_version": 1,
                                  "before": {"status": before, "version": version},
                                  "after": {"status": target, "version": new_version}})
            cursor.execute("""INSERT INTO audit_log
                (id, project_id, task_uuid, actor, action, entity_type, entity_id, details)
                VALUES (%s,%s,%s,%s,%s,'task',%s,%s::jsonb)""",
                (str(uuid4()), project, task_uuid, actor, f"task.{action}", entity_id, details))
            event = {"complete": "TaskCompleted", "delete": "TaskDeleted",
                     "pause": "TaskPaused", "resume": "TaskResumed"}[action]
            payload = json.dumps({"task_id": entity_id, "before_status": before,
                                  "after_status": target, "version": new_version})
            cursor.execute("""INSERT INTO events
                (id, project_id, task_uuid, event_type, source, payload)
                VALUES (%s,%s,%s,%s,'gateway',%s::jsonb)""",
                (str(uuid4()), project, task_uuid, event, payload))
            return True, f"Task {entity_id} {action}d"

    def create(
        self, project: str, title: str, mode: str, steps: int,
        depends_on: str | None, context: RequestContext | None,
    ) -> dict:
        project = validate_safe_id(project, "project")
        actor = self._principal(project, context)
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Task title required")
        if not isinstance(mode, str) or not mode.strip():
            raise ValueError("Task mode required")
        if type(steps) is not int or steps < 1:
            raise ValueError("Task steps must be a positive integer")
        if depends_on is not None:
            depends_on = validate_safe_id(depends_on, "dependency")

        with self._transaction(project) as cursor:
            cursor.execute("SELECT id FROM projects WHERE id=%s AND status='active' FOR UPDATE", (project,))
            if cursor.fetchone() is None:
                raise ValueError("Active project not found")
            dependency_uuid = None
            if depends_on:
                cursor.execute("""SELECT task_uuid FROM tasks WHERE project_id=%s
                    AND (legacy_id=%s OR task_uuid::text=%s) AND status <> 'deleted'""",
                    (project, depends_on, depends_on))
                matches = cursor.fetchall()
                if len(matches) != 1:
                    raise TaskMutationConflict("Dependency not found or ambiguous", "task_dependency_conflict")
                dependency_uuid = matches[0][0]
            cursor.execute("SELECT coalesce(max(task_number), 0) FROM tasks WHERE project_id=%s", (project,))
            number = int(cursor.fetchone()[0]) + 1
            while True:
                legacy_id = f"T-{number:02d}" if number < 100 else f"T-{number}"
                cursor.execute("SELECT 1 FROM tasks WHERE project_id=%s AND legacy_id=%s LIMIT 1",
                               (project, legacy_id))
                if cursor.fetchone() is None:
                    break
                number += 1
            task_uuid = str(uuid4())
            cursor.execute("""INSERT INTO tasks
                (task_uuid, project_id, task_number, legacy_id, title, mode, status,
                 version, steps_done, steps_total, depends_on_uuid)
                VALUES (%s,%s,%s,%s,%s,%s,'todo',1,0,%s,%s)""",
                (task_uuid, project, number, legacy_id, title.strip(), mode.strip(), steps,
                 dependency_uuid))
            cursor.execute("""INSERT INTO audit_log
                (id, project_id, task_uuid, actor, action, entity_type, entity_id, details)
                VALUES (%s,%s,%s,%s,'task.create','task',%s,%s::jsonb)""",
                (str(uuid4()), project, task_uuid, actor, legacy_id,
                 json.dumps({"schema_version": 1, "after": {"status": "todo", "version": 1}})))
            cursor.execute("""INSERT INTO events
                (id, project_id, task_uuid, event_type, source, payload)
                VALUES (%s,%s,%s,'TaskCreated','gateway',%s::jsonb)""",
                (str(uuid4()), project, task_uuid,
                 json.dumps({"task_id": legacy_id, "version": 1})))
            return {"id": legacy_id, "task_uuid": task_uuid, "project": project,
                    "title": title.strip(), "mode": mode.strip(), "status": "todo",
                    "steps_done": 0, "steps_total": steps, "version": 1,
                    "depends_on": depends_on}

    def next_task(self, project: str, context: RequestContext | None) -> dict | None:
        project = validate_safe_id(project, "project")
        actor = self._principal(project, context)
        with self._transaction(project) as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (project,))
            cursor.execute("""SELECT task_uuid, legacy_id, title, mode, status,
                steps_done, steps_total, version FROM tasks WHERE project_id=%s
                AND status='in_progress' ORDER BY created_at, task_number LIMIT 1""", (project,))
            active = cursor.fetchone()
            if active:
                return self._task_dict(project, active)
            cursor.execute("""SELECT t.task_uuid, t.legacy_id, t.title, t.mode, t.status,
                t.steps_done, t.steps_total, t.version FROM tasks t
                LEFT JOIN tasks dependency ON dependency.task_uuid=t.depends_on_uuid
                    AND dependency.project_id=t.project_id
                WHERE t.project_id=%s AND t.status='todo'
                    AND (t.depends_on_uuid IS NULL OR dependency.status='done')
                ORDER BY t.created_at, t.task_number LIMIT 1 FOR UPDATE OF t""", (project,))
            candidate = cursor.fetchone()
            if candidate is None:
                return None
            task_uuid, legacy_id, title, mode, before, done, total, version = candidate
            cursor.execute("""UPDATE tasks SET status='in_progress', version=version+1,
                started_at=coalesce(started_at,now()), updated_at=now()
                WHERE task_uuid=%s AND project_id=%s AND status='todo'""", (task_uuid, project))
            if cursor.rowcount != 1:
                raise TaskMutationConflict("Task selection changed", "stale_task_version")
            entity_id = legacy_id or str(task_uuid)
            cursor.execute("""INSERT INTO audit_log
                (id, project_id, task_uuid, actor, action, entity_type, entity_id, details)
                VALUES (%s,%s,%s,%s,'task.next','task',%s,%s::jsonb)""",
                (str(uuid4()), project, task_uuid, actor, entity_id,
                 json.dumps({"schema_version": 1, "before": {"status": before, "version": version},
                             "after": {"status": "in_progress", "version": version + 1}})))
            cursor.execute("""INSERT INTO events
                (id, project_id, task_uuid, event_type, source, payload)
                VALUES (%s,%s,%s,'TaskNext','gateway',%s::jsonb)""",
                (str(uuid4()), project, task_uuid,
                 json.dumps({"task_id": entity_id, "title": title, "version": version + 1})))
            return {"id": entity_id, "task_uuid": str(task_uuid), "project": project,
                    "title": title, "mode": mode, "status": "in_progress",
                    "steps_done": done, "steps_total": total, "version": version + 1}

    @staticmethod
    def _task_dict(project: str, row: tuple) -> dict:
        task_uuid, legacy_id, title, mode, status, done, total, version = row
        return {"id": legacy_id or str(task_uuid), "task_uuid": str(task_uuid),
                "project": project, "title": title, "mode": mode, "status": status,
                "steps_done": done, "steps_total": total, "version": version}
