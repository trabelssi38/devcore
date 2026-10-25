"""High-level Durable Run Engine orchestrating store, scheduler, and executor."""

from __future__ import annotations

import concurrent.futures
import os
import threading
import time
from pathlib import Path
from uuid import uuid4

from ..context import validate_project_id
from ..db import get_local_data_root
from .effects import EffectIdempotencyStore
from .postgres_effects import PostgresEffectIdempotencyStore
from .postgres_store import PostgresRunStore
from .executor import ProcessRunExecutor
from .models import (
    RunQuotaConfig,
    RunRecord,
    RunSubmission,
)
from .scheduler import FairRunScheduler
from .store import SqliteRunStore


class DurableRunEngine:
    """Unified durable execution engine for resilient, multi-tenant workflows."""

    def __init__(
        self,
        store: SqliteRunStore | PostgresRunStore | None = None,
        quota_config: RunQuotaConfig | None = None,
        executor: ProcessRunExecutor | None = None,
        local_root: Path | None = None,
    ):
        self.local_root = local_root or get_local_data_root()
        self.store = store if store is not None else self._configured_store()
        self.quota_config = quota_config or RunQuotaConfig()
        self.scheduler = FairRunScheduler(self.store, self.quota_config)
        self.executor = executor or ProcessRunExecutor(
            local_root=self.local_root,
            output_limit_bytes=self.quota_config.output_limit_bytes,
        )
        self.effects = (
            PostgresEffectIdempotencyStore(self.store)
            if isinstance(self.store, PostgresRunStore)
            else EffectIdempotencyStore(self.store)
        )
        self._worker_thread: threading.Thread | None = None
        self._worker_running = False
        self._wake_event = threading.Event()
        self._stop_event = threading.Event()
        self._thread_pool: concurrent.futures.ThreadPoolExecutor | None = None
        self._active_futures: set[concurrent.futures.Future] = set()
        self._futures_lock = threading.Lock()
        self._active_runs: set[str] = set()
        self._runs_lock = threading.Lock()

    @staticmethod
    def _configured_store() -> SqliteRunStore | PostgresRunStore:
        mode = os.environ.get("DEVCORE_RUN_STORE", "").strip().lower()
        team_mode = (
            os.environ.get("DEVCORE_TASK_READ_MODE", "").strip().lower() == "postgres"
            or os.environ.get("DEVCORE_IDENTITY_READ_MODE", "").strip().lower() == "postgres"
        )
        if mode not in {"", "sqlite", "postgres"}:
            raise ValueError(f"Invalid DEVCORE_RUN_STORE: {mode}")
        if mode == "sqlite" and team_mode:
            raise ValueError("SQLite run store is forbidden in PostgreSQL team mode")
        if mode == "postgres" or team_mode:
            dsn = os.environ.get("DEVCORE_DATABASE_URL", "").strip()
            if not dsn:
                raise ValueError("DEVCORE_DATABASE_URL is required for PostgreSQL runs")
            return PostgresRunStore(dsn)
        return SqliteRunStore()



    def submit_run(self, submission: RunSubmission) -> tuple[RunRecord, bool]:
        """Submit a run. Idempotent on idempotency_key; enforces backpressure."""
        submission.project_id = validate_project_id(submission.project_id)
        # Check idempotency first before backpressure queue check
        if submission.idempotency_key:
            existing = self.store.get_run_by_idempotency_key(
                submission.project_id, submission.idempotency_key
            )
            if existing is not None:
                return existing, False

        self.scheduler.check_submission_admission(submission)
        return self.store.save_submission(submission)

    def wake_worker(self) -> None:
        """Signal background worker to run execution steps."""
        self._wake_event.set()

    def start_worker(self, poll_interval: float = 0.5) -> None:
        """Start a dedicated background execution thread with concurrent run dispatch."""
        if self._worker_running:
            return
        if isinstance(self.store, PostgresRunStore):
            self.store.verify_ready()
        self._stop_event.clear()
        self._worker_running = True
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, self.quota_config.global_max_running),
            thread_name_prefix="devcore-run-exec",
        )

        def _worker_loop():
            while self._worker_running:
                try:
                    self.recover_interrupted_runs()

                    # Clean up completed futures
                    with self._futures_lock:
                        self._active_futures = {f for f in self._active_futures if not f.done()}
                        active_count = len(self._active_futures)

                    # Dispatch runs up to available concurrency slots
                    while self._worker_running and active_count < self.quota_config.global_max_running:
                        candidate = self.scheduler.select_next_run()
                        if candidate is None:
                            break

                        worker_token = f"wtoken-{uuid4().hex[:12]}"
                        claimed = self.store.claim_run(candidate.id, worker_token)
                        if claimed is None:
                            break

                        def _run_task(c=claimed, wt=worker_token):
                            with self._runs_lock:
                                self._active_runs.add(c.id)
                            try:
                                self._execute_claimed_run(c, wt)
                            finally:
                                with self._runs_lock:
                                    self._active_runs.discard(c.id)
                                self.wake_worker()

                        future = self._thread_pool.submit(_run_task)
                        with self._futures_lock:
                            self._active_futures.add(future)
                            active_count = len(self._active_futures)

                except Exception:
                    pass

                self._wake_event.wait(timeout=poll_interval)
                self._wake_event.clear()

        self._worker_thread = threading.Thread(
            target=_worker_loop, daemon=True, name="devcore-run-worker"
        )
        self._worker_thread.start()

    def stop_worker(self, timeout: float = 3.0) -> None:
        """Stop background execution thread, interrupt active runs, and respect timeout."""
        start_time = time.monotonic()
        self._worker_running = False
        self._stop_event.set()
        self._wake_event.set()

        # 1. Immediately terminate child processes of active runs
        self.executor.interrupt_all()

        # 2. Mark active runs as cancellation requested in store
        with self._runs_lock:
            active_ids = list(self._active_runs)
        for rid in active_ids:
            try:
                self.store.request_cancellation(rid)
            except Exception:
                pass

        # 3. Join worker dispatcher thread within remaining timeout
        elapsed = time.monotonic() - start_time
        remaining = max(0.0, timeout - elapsed)
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=remaining)
        self._worker_thread = None

        # 4. Await active thread pool futures within remaining timeout
        elapsed = time.monotonic() - start_time
        remaining = max(0.0, timeout - elapsed)
        with self._futures_lock:
            active_futs = list(self._active_futures)

        if active_futs and remaining > 0:
            concurrent.futures.wait(active_futs, timeout=remaining)

        # 5. Non-blocking shutdown of thread pool to prevent hanging past timeout
        if self._thread_pool:
            self._thread_pool.shutdown(wait=False, cancel_futures=True)
            self._thread_pool = None



    def get_run(self, run_id: str) -> RunRecord | None:
        return self.store.get_run(run_id)

    def list_runs(
        self,
        project_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[RunRecord], int]:
        return self.store.list_runs(
            project_id=project_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    def cancel_run(self, run_id: str) -> RunRecord:
        return self.store.request_cancellation(run_id)

    def pause_run(self, run_id: str) -> RunRecord:
        return self.store.pause_run(run_id)

    def resume_run(self, run_id: str) -> RunRecord:
        return self.store.resume_run(run_id)

    def approve_run(self, run_id: str) -> RunRecord:
        return self.store.approve_run(run_id)

    def recover_interrupted_runs(self, heartbeat_timeout_seconds: float | None = None) -> list[str]:
        timeout = (
            heartbeat_timeout_seconds
            if heartbeat_timeout_seconds is not None
            else self.quota_config.heartbeat_timeout_seconds
        )
        return self.store.recover_stale_or_interrupted(timeout)

    def step(self, project_id: str | None = None) -> RunRecord | None:
        """Single cooperative scheduling and execution tick."""
        self.recover_interrupted_runs()

        candidate = self.scheduler.select_next_run(project_id=project_id)
        if candidate is None:
            return None

        worker_token = f"wtoken-{uuid4().hex[:12]}"
        claimed = self.store.claim_run(candidate.id, worker_token)
        if claimed is None:
            return None

        return self._execute_claimed_run(claimed, worker_token)

    def _execute_claimed_run(self, claimed: RunRecord, worker_token: str) -> RunRecord:
        """Execute a claimed run record with heartbeating and cancellation containment."""
        outcome, exit_code, stdout, stderr = self.executor.execute(
            claimed,
            worker_token=worker_token,
            heartbeat_callback=lambda: self.store.record_heartbeat(claimed.id, worker_token),
            heartbeat_interval_seconds=self.quota_config.heartbeat_interval_seconds,
            check_cancellation_callback=lambda: bool(
                self._stop_event.is_set()
                or getattr(self.store.get_run(claimed.id), "cancellation_requested", False)
            ),
            check_pause_callback=lambda: bool(
                getattr(self.store.get_run(claimed.id), "status", None) == "paused"
            ),
        )

        if outcome == "paused":
            # Run was paused while running; process was terminated cleanly.
            return self.store.get_run(claimed.id)
        elif outcome == "timed_out":
            return self.store.timeout_run(claimed.id, worker_token, output=stdout, error=stderr)
        elif outcome == "cancelled":
            return self.store.confirm_cancellation(
                claimed.id, worker_token=worker_token, output=stdout, error=stderr
            )
        else:
            return self.store.complete_run(
                claimed.id,
                worker_token,
                exit_code=exit_code,
                output=stdout,
                error=stderr if exit_code != 0 else None,
            )

