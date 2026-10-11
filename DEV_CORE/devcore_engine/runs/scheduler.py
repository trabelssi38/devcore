"""Fair scheduler and quota admission controller for durable runs."""

from __future__ import annotations

from .models import (
    RunBackpressureError,
    RunQuotaConfig,
    RunRecord,
    RunSubmission,
)
from .store import SqliteRunStore


class FairRunScheduler:
    """Fair scheduler with multi-tenant rotation and strict quota boundaries."""

    def __init__(
        self,
        store: SqliteRunStore,
        quota_config: RunQuotaConfig | None = None,
    ):
        self.store = store
        self.quota_config = quota_config or RunQuotaConfig()

    def check_submission_admission(self, submission: RunSubmission) -> None:
        """Validate queue backpressure before accepting submission."""
        queued_count = self.store.count_queued_runs(submission.project_id)
        if queued_count >= self.quota_config.max_queued_per_project:
            raise RunBackpressureError(
                f"Queue backpressure limit exceeded for project {submission.project_id}: "
                f"{queued_count} queued (limit: {self.quota_config.max_queued_per_project})"
            )

    def select_next_run(self, project_id: str | None = None) -> RunRecord | None:
        """Select next eligible queued run using fair round-robin scheduling."""
        total_active, by_project = self.store.count_active_runs()

        # Check global slot saturation (default: 2 slots)
        if total_active >= self.quota_config.global_max_running:
            return None

        projects_with_queued = self.store.list_projects_with_queued_runs()
        if not projects_with_queued:
            return None

        if project_id is not None:
            projects_with_queued = [p for p in projects_with_queued if p[0] == project_id]
            if not projects_with_queued:
                return None

        # Filter out projects at capacity (default: 1 slot per project)
        eligible = [
            (pid, oldest)
            for (pid, oldest) in projects_with_queued
            if by_project.get(pid, 0) < self.quota_config.project_max_running
        ]
        if not eligible:
            return None

        # Fair sorting:
        # 1. Projects with fewest running slots (0 running comes before 1 running)
        # 2. Oldest queued run timestamp
        eligible.sort(key=lambda item: (by_project.get(item[0], 0), item[1]))

        winning_project_id = eligible[0][0]
        return self.store.get_oldest_queued_run(winning_project_id)

