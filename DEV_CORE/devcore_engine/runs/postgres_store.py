"""Project-scoped PostgreSQL persistence for durable runs.

Historical imported rows remain visible, but only rows explicitly marked
execution_ready may enter the worker queue.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
import json
from urllib.parse import unquote, urlparse
from uuid import uuid4

from ..context import validate_project_id
from .models import RunFencingError, RunNotFoundError, RunRecord, RunSubmission, RunTransitionError


def _json(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


def _datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _row(cursor, values):
    if values is None:
        return None
    return {column[0]: value for column, value in zip(cursor.description, values)}


def _record(row):
    if row is None:
        return None
    return RunRecord(
        id=row["id"], project_id=row["project_id"], task_id=row.get("task_id"),
        title=row.get("title") or "Historical run", status=row["status"],
        command=_json(row.get("command"), []),
        timeout_seconds=float(row.get("timeout_seconds") or 300),
        attempt_number=int(row.get("attempt_number") or 0),
        max_attempts=int(row.get("max_attempts") or 3),
        worker_token=row.get("worker_token"),
        heartbeat_at=_datetime(row.get("heartbeat_at")),
        cancellation_requested=bool(row.get("cancellation_requested")),
        output=row.get("output"), error=row.get("error"), exit_code=row.get("exit_code"),
        idempotency_key=row.get("idempotency_key"), actor=row.get("actor") or "system",
        env=_json(row.get("env"), {}), metadata=_json(row.get("metadata"), {}),
        created_at=_datetime(row.get("created_at")) or datetime.now(UTC),
        started_at=_datetime(row.get("started_at")),
        finished_at=_datetime(row.get("finished_at")),
        updated_at=_datetime(row.get("updated_at")) or datetime.now(UTC),
    )


def _record_project_job_result(cursor, project_id: str, row: dict) -> None:
    metadata = _json(row.get("metadata"), {})
    if metadata.get("job_kind") in {"git_scan", "repowise_index"}:
        kind = metadata["job_kind"]
        cursor.execute("""INSERT INTO events
            (id,project_id,run_id,event_type,source,payload)
            VALUES (%s,%s,%s,'project_job.finished',%s,%s::jsonb)
            ON CONFLICT (id) DO NOTHING""",
            ("event-job-terminal-" + row["id"], project_id, row["id"], kind,
             json.dumps({"status": row["status"], "exit_code": row.get("exit_code")})))
    if metadata.get("schedule_id"):
        cursor.execute("""INSERT INTO schedule_history
            (id,schedule_id,run_id,event_type,status,details)
            VALUES (%s,%s,%s,'finished',%s,%s::jsonb)
            ON CONFLICT (id) DO NOTHING""",
            ("schedule-result-" + row["id"], metadata["schedule_id"], row["id"],
             row["status"], json.dumps({"exit_code": row.get("exit_code")})))


class PostgresRunStore:
    """Uses an explicit transaction-local RLS project for every run query."""

    def __init__(self, dsn: str):
        parsed = urlparse(dsn.replace("postgresql+pg8000://", "postgresql://", 1))
        if parsed.scheme != "postgresql" or parsed.hostname not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("PostgreSQL run store requires a local PostgreSQL DSN")
        if not parsed.username or not parsed.path or parsed.path == "/":
            raise ValueError("PostgreSQL run store requires user and database")
        self._options = {
            "user": unquote(parsed.username), "password": unquote(parsed.password or ""),
            "host": parsed.hostname, "port": parsed.port or 5432,
            "database": parsed.path.lstrip("/"),
        }

    def _connect(self):
        import pg8000.dbapi
        return pg8000.dbapi.connect(**self._options)

    def verify_ready(self) -> None:
        """Refuse worker startup when the durable schema or RLS is absent."""
        with self._transaction("devcore") as cursor:
            cursor.execute("""SELECT execution_ready, command, worker_token,
                heartbeat_at, idempotency_key FROM runs LIMIT 0""")
            cursor.execute("SELECT status, result FROM external_effects LIMIT 0")
            cursor.execute("""SELECT r.rolsuper, r.rolbypassrls,
                (SELECT relrowsecurity AND relforcerowsecurity FROM pg_class
                 WHERE oid='runs'::regclass),
                (SELECT relrowsecurity AND relforcerowsecurity FROM pg_class
                 WHERE oid='external_effects'::regclass)
                FROM pg_roles r WHERE r.rolname=current_user""")
            flags = cursor.fetchone()
            if flags is None or flags[0] or flags[1] or not flags[2] or not flags[3]:
                raise RuntimeError("PostgreSQL run role or table RLS is not safe for workers")

    @contextmanager
    def _transaction(self, project_id: str):
        project_id = validate_project_id(project_id)
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT set_config('app.current_project_id', %s, true)", (project_id,))
            yield cursor
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _projects(self) -> list[str]:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM projects WHERE status = 'active' ORDER BY id")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.rollback()
            conn.close()

    def _run_project(self, run_id: str) -> str | None:
        for project_id in self._projects():
            with self._transaction(project_id) as cursor:
                cursor.execute("SELECT 1 FROM runs WHERE project_id = %s AND id = %s", (project_id, run_id))
                if cursor.fetchone() is not None:
                    return project_id
        return None

    def save_submission(self, submission: RunSubmission) -> tuple[RunRecord, bool]:
        project_id = validate_project_id(submission.project_id)
        command = submission.normalized_command()
        if not command:
            raise ValueError("Run command cannot be empty")
        run_id = f"run-{uuid4().hex[:12]}"
        with self._transaction(project_id) as cursor:
            cursor.execute("""INSERT INTO runs
                (id, project_id, task_id, title, status, command, timeout_seconds,
                 attempt_number, max_attempts, cancellation_requested, idempotency_key,
                 actor, env, metadata, execution_ready)
                VALUES (%s,%s,%s,%s,'queued',%s::jsonb,%s,0,3,false,%s,%s,%s::jsonb,%s::jsonb,true)
                ON CONFLICT DO NOTHING RETURNING *""",
                (run_id, project_id, submission.task_id, submission.title,
                 json.dumps(command), float(submission.timeout_seconds),
                 submission.idempotency_key, submission.actor, json.dumps(submission.env),
                 json.dumps(submission.metadata)))
            saved = _row(cursor, cursor.fetchone())
            if saved is not None:
                return _record(saved), True
            if not submission.idempotency_key:
                raise RuntimeError("Run insertion conflicted without idempotency key")
            cursor.execute("""SELECT * FROM runs WHERE project_id=%s AND idempotency_key=%s
                AND execution_ready""", (project_id, submission.idempotency_key))
            existing = _row(cursor, cursor.fetchone())
            if existing is None:
                raise RuntimeError("Run idempotency conflict was not readable")
            return _record(existing), False

    def get_run(self, run_id: str) -> RunRecord | None:
        project_id = self._run_project(run_id)
        if project_id is None:
            return None
        with self._transaction(project_id) as cursor:
            cursor.execute("SELECT * FROM runs WHERE project_id=%s AND id=%s", (project_id, run_id))
            return _record(_row(cursor, cursor.fetchone()))

    def get_run_by_idempotency_key(self, project_id: str, key: str) -> RunRecord | None:
        with self._transaction(project_id) as cursor:
            cursor.execute("""SELECT * FROM runs WHERE project_id=%s AND idempotency_key=%s
                AND execution_ready""", (project_id, key))
            return _record(_row(cursor, cursor.fetchone()))

    def list_runs(self, project_id: str | None = None, status: str | None = None,
                  limit: int = 50, offset: int = 0) -> tuple[list[RunRecord], int]:
        if project_id is None:
            raise ValueError("PostgreSQL run listing requires an explicit project")
        with self._transaction(project_id) as cursor:
            cursor.execute("""SELECT count(*) FROM runs WHERE project_id=%s
                AND (%s IS NULL OR status=%s)""", (project_id, status, status))
            total = cursor.fetchone()[0]
            cursor.execute("""SELECT * FROM runs WHERE project_id=%s
                AND (%s IS NULL OR status=%s) ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                (project_id, status, status, max(1, limit), max(0, offset)))
            return [_record(_row(cursor, item)) for item in cursor.fetchall()], total

    def count_active_runs(self) -> tuple[int, dict[str, int]]:
        counts = {}
        for project_id in self._projects():
            with self._transaction(project_id) as cursor:
                cursor.execute("""SELECT count(*) FROM runs WHERE project_id=%s
                    AND execution_ready AND status='running'""", (project_id,))
                counts[project_id] = cursor.fetchone()[0]
        return sum(counts.values()), counts

    def count_queued_runs(self, project_id: str | None = None) -> int:
        if project_id is None:
            return sum(self.count_queued_runs(project) for project in self._projects())
        with self._transaction(project_id) as cursor:
            cursor.execute("""SELECT count(*) FROM runs WHERE project_id=%s
                AND execution_ready AND status='queued'""", (project_id,))
            return cursor.fetchone()[0]

    def list_projects_with_queued_runs(self) -> list[tuple[str, datetime]]:
        pending = []
        for project_id in self._projects():
            with self._transaction(project_id) as cursor:
                cursor.execute("""SELECT min(created_at) FROM runs WHERE project_id=%s
                    AND execution_ready AND status='queued'""", (project_id,))
                oldest = cursor.fetchone()[0]
                if oldest is not None:
                    pending.append((project_id, _datetime(oldest)))
        return sorted(pending, key=lambda item: item[1])

    def get_oldest_queued_run(self, project_id: str) -> RunRecord | None:
        with self._transaction(project_id) as cursor:
            cursor.execute("""SELECT * FROM runs WHERE project_id=%s AND execution_ready
                AND status='queued' ORDER BY created_at, id LIMIT 1""", (project_id,))
            return _record(_row(cursor, cursor.fetchone()))

    def claim_run(self, run_id: str, worker_token: str) -> RunRecord | None:
        project_id = self._run_project(run_id)
        if project_id is None:
            return None
        with self._transaction(project_id) as cursor:
            cursor.execute("""UPDATE runs SET status='running', attempt_number=attempt_number+1,
                worker_token=%s, started_at=coalesce(started_at,now()), heartbeat_at=now(),
                updated_at=now() WHERE id=%s AND project_id=%s AND execution_ready
                AND status='queued' RETURNING *""", (worker_token, run_id, project_id))
            return _record(_row(cursor, cursor.fetchone()))

    def record_heartbeat(self, run_id: str, worker_token: str) -> bool:
        project_id = self._run_project(run_id)
        if project_id is None:
            return False
        with self._transaction(project_id) as cursor:
            cursor.execute("""UPDATE runs SET heartbeat_at=now(), updated_at=now()
                WHERE id=%s AND project_id=%s AND execution_ready AND status='running'
                AND worker_token=%s""", (run_id, project_id, worker_token))
            return cursor.rowcount == 1

    def _required_project(self, run_id: str) -> str:
        project_id = self._run_project(run_id)
        if project_id is None:
            raise RunNotFoundError(f"Run {run_id} not found")
        return project_id

    def _finish(self, run_id: str, worker_token: str, *, status: str,
                exit_code: int | None, output: str, error: str | None) -> RunRecord:
        project_id = self._required_project(run_id)
        with self._transaction(project_id) as cursor:
            cursor.execute("""UPDATE runs SET status=%s, exit_code=%s, output=%s, error=%s,
                finished_at=now(), updated_at=now() WHERE id=%s AND project_id=%s
                AND execution_ready AND status='running' AND worker_token=%s RETURNING *""",
                (status, exit_code, output, error, run_id, project_id, worker_token))
            updated = _row(cursor, cursor.fetchone())
            if updated is not None:
                _record_project_job_result(cursor, project_id, updated)
                return _record(updated)
            cursor.execute("SELECT status, worker_token FROM runs WHERE id=%s AND project_id=%s",
                           (run_id, project_id))
            current = cursor.fetchone()
            if current is None:
                raise RunNotFoundError(f"Run {run_id} not found")
            if current[1] != worker_token:
                raise RunFencingError(f"Worker token mismatch for run {run_id}")
            raise RunTransitionError(f"Cannot complete run {run_id} from status {current[0]}")

    def complete_run(self, run_id: str, worker_token: str, exit_code: int,
                     output: str = "", error: str | None = None) -> RunRecord:
        return self._finish(run_id, worker_token,
                            status="succeeded" if exit_code == 0 else "failed",
                            exit_code=exit_code, output=output, error=error)

    def timeout_run(self, run_id: str, worker_token: str, output: str = "",
                    error: str | None = None) -> RunRecord:
        return self._finish(run_id, worker_token, status="timed_out", exit_code=None,
                            output=output, error=error or "Run timed out")

    def request_cancellation(self, run_id: str) -> RunRecord:
        project_id = self._required_project(run_id)
        with self._transaction(project_id) as cursor:
            cursor.execute("SELECT * FROM runs WHERE id=%s AND project_id=%s FOR UPDATE",
                           (run_id, project_id))
            record = _record(_row(cursor, cursor.fetchone()))
            if record is None:
                raise RunNotFoundError(f"Run {run_id} not found")
            if record.is_terminal():
                return record
            if record.status in {"queued", "waiting_approval", "paused"}:
                cursor.execute("""UPDATE runs SET status='cancelled', cancellation_requested=true,
                    finished_at=now(), updated_at=now() WHERE id=%s AND project_id=%s
                    AND execution_ready RETURNING *""", (run_id, project_id))
            else:
                cursor.execute("""UPDATE runs SET cancellation_requested=true, updated_at=now()
                    WHERE id=%s AND project_id=%s AND execution_ready RETURNING *""",
                    (run_id, project_id))
            updated = _row(cursor, cursor.fetchone())
            if updated is None:
                raise RunTransitionError("Historical run is not executable")
            if updated["status"] == "cancelled":
                _record_project_job_result(cursor, project_id, updated)
            return _record(updated)

    def confirm_cancellation(self, run_id: str, worker_token: str | None = None,
                             output: str = "", error: str | None = None) -> RunRecord:
        project_id = self._required_project(run_id)
        with self._transaction(project_id) as cursor:
            cursor.execute("""UPDATE runs SET status='cancelled', cancellation_requested=true,
                output=%s, error=%s, finished_at=now(), updated_at=now()
                WHERE id=%s AND project_id=%s AND execution_ready AND status='running'
                AND (%s IS NULL OR worker_token=%s) RETURNING *""",
                (output, error or "Run cancelled by user", run_id, project_id,
                 worker_token, worker_token))
            updated = _row(cursor, cursor.fetchone())
            if updated is None:
                raise RunTransitionError(f"Cannot confirm cancellation of run {run_id}")
            _record_project_job_result(cursor, project_id, updated)
            return _record(updated)

    def pause_run(self, run_id: str) -> RunRecord:
        project_id = self._required_project(run_id)
        with self._transaction(project_id) as cursor:
            cursor.execute("""UPDATE runs SET status='paused', worker_token=NULL,
                updated_at=now() WHERE id=%s AND project_id=%s AND execution_ready
                AND status IN ('queued','running','waiting_approval') RETURNING *""",
                (run_id, project_id))
            updated = _row(cursor, cursor.fetchone())
            if updated is None:
                raise RunTransitionError(f"Cannot pause run {run_id}")
            return _record(updated)

    def resume_run(self, run_id: str) -> RunRecord:
        project_id = self._required_project(run_id)
        with self._transaction(project_id) as cursor:
            cursor.execute("""UPDATE runs SET status='queued', worker_token=NULL,
                updated_at=now() WHERE id=%s AND project_id=%s AND execution_ready
                AND status='paused' RETURNING *""", (run_id, project_id))
            updated = _row(cursor, cursor.fetchone())
            if updated is None:
                raise RunTransitionError(f"Cannot resume run {run_id}")
            return _record(updated)

    def request_approval(self, run_id: str, worker_token: str) -> RunRecord:
        project_id = self._required_project(run_id)
        with self._transaction(project_id) as cursor:
            cursor.execute("""UPDATE runs SET status='waiting_approval', updated_at=now()
                WHERE id=%s AND project_id=%s AND execution_ready AND status='running'
                AND worker_token=%s RETURNING *""", (run_id, project_id, worker_token))
            updated = _row(cursor, cursor.fetchone())
            if updated is None:
                raise RunTransitionError(f"Cannot request approval of run {run_id}")
            return _record(updated)

    def approve_run(self, run_id: str) -> RunRecord:
        project_id = self._required_project(run_id)
        with self._transaction(project_id) as cursor:
            cursor.execute("""UPDATE runs SET status='queued', worker_token=NULL,
                updated_at=now() WHERE id=%s AND project_id=%s AND execution_ready
                AND status='waiting_approval' RETURNING *""", (run_id, project_id))
            updated = _row(cursor, cursor.fetchone())
            if updated is None:
                raise RunTransitionError(f"Cannot approve run {run_id}")
            return _record(updated)

    def recover_stale_or_interrupted(self, heartbeat_timeout_seconds: float = 15.0) -> list[str]:
        cutoff = datetime.now(UTC) - timedelta(seconds=heartbeat_timeout_seconds)
        recovered = []
        for project_id in self._projects():
            with self._transaction(project_id) as cursor:
                cursor.execute("""SELECT id, attempt_number, max_attempts FROM runs
                    WHERE project_id=%s AND execution_ready AND status='running'
                    AND (heartbeat_at IS NULL OR heartbeat_at < %s)
                    FOR UPDATE SKIP LOCKED""", (project_id, cutoff))
                for run_id, attempt, maximum in cursor.fetchall():
                    if attempt < maximum:
                        cursor.execute("""UPDATE runs SET status='queued', worker_token=NULL,
                            updated_at=now() WHERE id=%s AND project_id=%s""",
                            (run_id, project_id))
                    else:
                        cursor.execute("""UPDATE runs SET status='timed_out',
                            error='execution_heartbeat_expired', finished_at=now(),
                            updated_at=now() WHERE id=%s AND project_id=%s RETURNING *""",
                            (run_id, project_id))
                        terminal = _row(cursor, cursor.fetchone())
                        if terminal is not None:
                            _record_project_job_result(cursor, project_id, terminal)
                    recovered.append(run_id)
        return recovered
