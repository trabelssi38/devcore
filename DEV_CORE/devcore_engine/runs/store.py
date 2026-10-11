"""Persistent SQLite store for durable runs and external effects idempotency."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

from ..context import validate_project_id
from ..db import get_local_data_root
from .models import (
    RunFencingError,
    RunNotFoundError,
    RunRecord,
    RunSubmission,
    RunTransitionError,
)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _parse_iso(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except Exception:
        return None


class SqliteRunStore:
    """ACID transactional repository for durable runs."""

    def __init__(self, db_path: Path | str | None = None):
        if db_path is None:
            local_root = get_local_data_root()
            runs_dir = local_root / "runs"
            runs_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = runs_dir / "runs.db"
        else:
            self.db_path = Path(db_path)
            if self.db_path != Path(":memory:"):
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=10.0,
            check_same_thread=False,
            isolation_level="DEFERRED",
        )
        conn.row_factory = sqlite3.Row
        if str(self.db_path) != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    task_id TEXT,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    command TEXT NOT NULL,
                    timeout_seconds REAL NOT NULL DEFAULT 300.0,
                    attempt_number INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    worker_token TEXT,
                    heartbeat_at TEXT,
                    cancellation_requested INTEGER NOT NULL DEFAULT 0,
                    output TEXT,
                    error TEXT,
                    exit_code INTEGER,
                    idempotency_key TEXT,
                    actor TEXT NOT NULL DEFAULT 'system',
                    env TEXT NOT NULL DEFAULT '{}',
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS uq_runs_proj_idemp 
                    ON runs(project_id, idempotency_key) 
                    WHERE idempotency_key IS NOT NULL;

                CREATE INDEX IF NOT EXISTS idx_runs_project_status 
                    ON runs(project_id, status);

                CREATE INDEX IF NOT EXISTS idx_runs_status_created 
                    ON runs(status, created_at);

                CREATE TABLE IF NOT EXISTS external_effects (
                    project_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    effect_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    PRIMARY KEY (project_id, idempotency_key, effect_type)
                );
                """
            )

    def _row_to_record(self, row: sqlite3.Row) -> RunRecord:
        return RunRecord(
            id=row["id"],
            project_id=row["project_id"],
            task_id=row["task_id"],
            title=row["title"],
            status=row["status"],
            command=json.loads(row["command"]),
            timeout_seconds=float(row["timeout_seconds"]),
            attempt_number=int(row["attempt_number"]),
            max_attempts=int(row["max_attempts"]),
            worker_token=row["worker_token"],
            heartbeat_at=_parse_iso(row["heartbeat_at"]),
            cancellation_requested=bool(row["cancellation_requested"]),
            output=row["output"],
            error=row["error"],
            exit_code=row["exit_code"],
            idempotency_key=row["idempotency_key"],
            actor=row["actor"],
            env=json.loads(row["env"] or "{}"),
            metadata=json.loads(row["metadata"] or "{}"),
            created_at=_parse_iso(row["created_at"]) or datetime.now(UTC),
            started_at=_parse_iso(row["started_at"]),
            finished_at=_parse_iso(row["finished_at"]),
            updated_at=_parse_iso(row["updated_at"]) or datetime.now(UTC),
        )

    def save_submission(self, submission: RunSubmission) -> tuple[RunRecord, bool]:
        """Save a new run submission. Idempotent on (project_id, idempotency_key)."""
        project_id = validate_project_id(submission.project_id)
        now = datetime.now(UTC)
        now_str = now.isoformat()

        with self._connect() as conn:
            if submission.idempotency_key:
                cursor = conn.execute(
                    "SELECT * FROM runs WHERE project_id = ? AND idempotency_key = ?",
                    (project_id, submission.idempotency_key),
                )
                row = cursor.fetchone()
                if row is not None:
                    return self._row_to_record(row), False

            run_id = f"run-{uuid4().hex[:12]}"
            cmd_json = json.dumps(submission.normalized_command())
            env_json = json.dumps(submission.env)
            meta_json = json.dumps(submission.metadata)

            conn.execute(
                """
                INSERT INTO runs (
                    id, project_id, task_id, title, status, command,
                    timeout_seconds, attempt_number, max_attempts,
                    worker_token, heartbeat_at, cancellation_requested,
                    output, error, exit_code, idempotency_key, actor,
                    env, metadata, created_at, started_at, finished_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, 'queued', ?,
                    ?, 0, 3,
                    NULL, NULL, 0,
                    NULL, NULL, NULL, ?, ?,
                    ?, ?, ?, NULL, NULL, ?
                )
                """,
                (
                    run_id,
                    project_id,
                    submission.task_id,
                    submission.title,
                    cmd_json,
                    float(submission.timeout_seconds),
                    submission.idempotency_key,
                    submission.actor,
                    env_json,
                    meta_json,
                    now_str,
                    now_str,
                ),
            )
            cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            return self._row_to_record(cursor.fetchone()), True

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._connect() as conn:
            cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_record(row)

    def get_run_by_idempotency_key(
        self, project_id: str, idempotency_key: str
    ) -> RunRecord | None:
        """Fetch existing run by (project_id, idempotency_key)."""
        project_id = validate_project_id(project_id)
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM runs WHERE project_id = ? AND idempotency_key = ?",
                (project_id, idempotency_key),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_record(row)

    def list_runs(
        self,
        project_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[RunRecord], int]:
        query = "SELECT * FROM runs"
        count_query = "SELECT COUNT(*) FROM runs"
        params: list[object] = []
        conditions: list[str] = []

        if project_id:
            conditions.append("project_id = ?")
            params.append(project_id)
        if status:
            conditions.append("status = ?")
            params.append(status)

        if conditions:
            clause = " WHERE " + " AND ".join(conditions)
            query += clause
            count_query += clause

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"

        with self._connect() as conn:
            total = conn.execute(count_query, params).fetchone()[0]
            cursor = conn.execute(query, [*params, max(1, limit), max(0, offset)])
            records = [self._row_to_record(r) for r in cursor.fetchall()]
            return records, total

    def count_active_runs(self) -> tuple[int, dict[str, int]]:
        """Return (total_active, {project_id: count_active}) for status='running'."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT project_id, COUNT(*) FROM runs WHERE status = 'running' GROUP BY project_id"
            )
            by_project: dict[str, int] = {}
            total = 0
            for row in cursor.fetchall():
                pid = row[0]
                cnt = row[1]
                by_project[pid] = cnt
                total += cnt
            return total, by_project

    def count_queued_runs(self, project_id: str | None = None) -> int:
        with self._connect() as conn:
            if project_id:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM runs WHERE project_id = ? AND status = 'queued'",
                    (project_id,),
                )
            else:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM runs WHERE status = 'queued'"
                )
            return cursor.fetchone()[0]

    def list_projects_with_queued_runs(self) -> list[tuple[str, str]]:
        """Returns list of (project_id, oldest_queued_created_at)."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT project_id, MIN(created_at) AS oldest
                FROM runs
                WHERE status = 'queued'
                GROUP BY project_id
                ORDER BY oldest ASC
                """
            )
            return [(r[0], r[1]) for r in cursor.fetchall()]

    def get_oldest_queued_run(self, project_id: str) -> RunRecord | None:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM runs
                WHERE project_id = ? AND status = 'queued'
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (project_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_record(row)

    def claim_run(self, run_id: str, worker_token: str) -> RunRecord | None:
        """Atomically claim a queued run."""
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE runs
                SET status = 'running',
                    attempt_number = attempt_number + 1,
                    worker_token = ?,
                    started_at = coalesce(started_at, ?),
                    heartbeat_at = ?,
                    updated_at = ?
                WHERE id = ? AND status = 'queued'
                """,
                (worker_token, now, now, now, run_id),
            )
            if cursor.rowcount == 0:
                return None
            cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            return self._row_to_record(cursor.fetchone())

    def record_heartbeat(self, run_id: str, worker_token: str) -> bool:
        """Update heartbeat. Returns False if token mismatch (fencing)."""
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE runs
                SET heartbeat_at = ?,
                    updated_at = ?
                WHERE id = ? AND worker_token = ? AND status = 'running'
                """,
                (now, now, run_id, worker_token),
            )
            return cursor.rowcount > 0

    def complete_run(
        self,
        run_id: str,
        worker_token: str,
        exit_code: int,
        output: str = "",
        error: str | None = None,
    ) -> RunRecord:
        """Mark run succeeded or failed. Enforces worker token fencing."""
        record = self.get_run(run_id)
        if record is None:
            raise RunNotFoundError(f"Run {run_id} not found")
        if record.status != "running":
            raise RunTransitionError(
                f"Cannot complete run {run_id}: status is already '{record.status}' (expected 'running')"
            )
        if record.worker_token != worker_token:
            raise RunFencingError(
                f"Worker token mismatch for run {run_id}: expected {record.worker_token}, got {worker_token}"
            )

        new_status = "succeeded" if exit_code == 0 else "failed"
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE runs
                SET status = ?,
                    exit_code = ?,
                    output = ?,
                    error = ?,
                    finished_at = ?,
                    updated_at = ?
                WHERE id = ? AND worker_token = ? AND status = 'running'
                """,
                (new_status, exit_code, output, error, now, now, run_id, worker_token),
            )
            if cursor.rowcount == 0:
                refreshed = self.get_run(run_id)
                raise RunTransitionError(
                    f"Cannot complete run {run_id}: status changed to '{refreshed.status if refreshed else 'unknown'}'"
                )
            cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            return self._row_to_record(cursor.fetchone())

    def timeout_run(
        self,
        run_id: str,
        worker_token: str,
        output: str = "",
        error: str | None = None,
    ) -> RunRecord:
        """Mark run timed_out. Enforces worker token fencing."""
        record = self.get_run(run_id)
        if record is None:
            raise RunNotFoundError(f"Run {run_id} not found")
        if record.status != "running":
            raise RunTransitionError(
                f"Cannot timeout run {run_id}: status is already '{record.status}' (expected 'running')"
            )
        if record.worker_token != worker_token:
            raise RunFencingError(
                f"Worker token mismatch for run {run_id}: expected {record.worker_token}, got {worker_token}"
            )

        now = datetime.now(UTC).isoformat()
        err_msg = error or f"Run timed out after {record.timeout_seconds}s"
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE runs
                SET status = 'timed_out',
                    output = ?,
                    error = ?,
                    finished_at = ?,
                    updated_at = ?
                WHERE id = ? AND worker_token = ? AND status = 'running'
                """,
                (output, err_msg, now, now, run_id, worker_token),
            )
            if cursor.rowcount == 0:
                refreshed = self.get_run(run_id)
                raise RunTransitionError(
                    f"Cannot timeout run {run_id}: status changed to '{refreshed.status if refreshed else 'unknown'}'"
                )
            cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            return self._row_to_record(cursor.fetchone())

    def request_cancellation(self, run_id: str) -> RunRecord:
        """Request run cancellation."""
        record = self.get_run(run_id)
        if record is None:
            raise RunNotFoundError(f"Run {run_id} not found")
        if record.is_terminal():
            return record

        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            if record.status in {"queued", "waiting_approval", "paused"}:
                conn.execute(
                    """
                    UPDATE runs
                    SET status = 'cancelled',
                        cancellation_requested = 1,
                        finished_at = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (now, now, run_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE runs
                    SET cancellation_requested = 1,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (now, run_id),
                )
            cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            return self._row_to_record(cursor.fetchone())

    def confirm_cancellation(
        self,
        run_id: str,
        worker_token: str | None = None,
        output: str = "",
        error: str | None = None,
    ) -> RunRecord:
        """Confirm cancellation of a running run after process termination."""
        record = self.get_run(run_id)
        if record is None:
            raise RunNotFoundError(f"Run {run_id} not found")
        if worker_token and record.worker_token != worker_token:
            raise RunFencingError(
                f"Worker token mismatch for run {run_id}: expected {record.worker_token}, got {worker_token}"
            )

        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE runs
                SET status = 'cancelled',
                    cancellation_requested = 1,
                    output = ?,
                    error = ?,
                    finished_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (output, error or "Run cancelled by user", now, now, run_id),
            )
            cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            return self._row_to_record(cursor.fetchone())

    def pause_run(self, run_id: str) -> RunRecord:
        record = self.get_run(run_id)
        if record is None:
            raise RunNotFoundError(f"Run {run_id} not found")
        if record.is_terminal() or record.status == "paused":
            raise RunTransitionError(f"Cannot pause run in status {record.status}")

        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE runs
                SET status = 'paused',
                    worker_token = NULL,
                    updated_at = ?
                WHERE id = ? AND status IN ('queued', 'running', 'waiting_approval')
                """,
                (now, run_id),
            )
            if cursor.rowcount == 0:
                refreshed = self.get_run(run_id)
                raise RunTransitionError(
                    f"Cannot pause run {run_id}: status changed to '{refreshed.status if refreshed else 'unknown'}'"
                )
            cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            return self._row_to_record(cursor.fetchone())

    def resume_run(self, run_id: str) -> RunRecord:
        record = self.get_run(run_id)
        if record is None:
            raise RunNotFoundError(f"Run {run_id} not found")
        if record.status != "paused":
            raise RunTransitionError(f"Cannot resume run in status {record.status}")

        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE runs
                SET status = 'queued',
                    worker_token = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (now, run_id),
            )
            cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            return self._row_to_record(cursor.fetchone())

    def request_approval(self, run_id: str, worker_token: str) -> RunRecord:
        record = self.get_run(run_id)
        if record is None:
            raise RunNotFoundError(f"Run {run_id} not found")
        if record.worker_token != worker_token:
            raise RunFencingError(f"Worker token mismatch for run {run_id}")
        if record.status != "running":
            raise RunTransitionError(f"Cannot request approval from status {record.status}")

        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE runs
                SET status = 'waiting_approval',
                    updated_at = ?
                WHERE id = ? AND worker_token = ?
                """,
                (now, run_id, worker_token),
            )
            cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            return self._row_to_record(cursor.fetchone())

    def approve_run(self, run_id: str) -> RunRecord:
        record = self.get_run(run_id)
        if record is None:
            raise RunNotFoundError(f"Run {run_id} not found")
        if record.status != "waiting_approval":
            raise RunTransitionError(f"Cannot approve run in status {record.status}")

        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE runs
                SET status = 'queued',
                    worker_token = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (now, run_id),
            )
            cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            return self._row_to_record(cursor.fetchone())

    def recover_stale_or_interrupted(
        self, heartbeat_timeout_seconds: float = 15.0
    ) -> list[str]:
        """Recovers crashed/interrupted running jobs whose heartbeat has expired."""
        cutoff = datetime.now(UTC) - timedelta(seconds=heartbeat_timeout_seconds)
        cutoff_iso = cutoff.isoformat()
        now_iso = datetime.now(UTC).isoformat()
        recovered: list[str] = []

        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT id, attempt_number, max_attempts
                FROM runs
                WHERE status = 'running'
                  AND (heartbeat_at IS NULL OR heartbeat_at < ?)
                """,
                (cutoff_iso,),
            )
            stale_runs = cursor.fetchall()
            for row in stale_runs:
                r_id = row["id"]
                attempt = row["attempt_number"]
                max_att = row["max_attempts"]
                if attempt < max_att:
                    conn.execute(
                        """
                        UPDATE runs
                        SET status = 'queued',
                            worker_token = NULL,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (now_iso, r_id),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE runs
                        SET status = 'timed_out',
                            error = 'execution_heartbeat_expired',
                            finished_at = ?,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (now_iso, now_iso, r_id),
                    )
                recovered.append(r_id)

        return recovered
