"""Idempotency store for external side-effects deduplication."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import json
from typing import Any

from .models import EffectAlreadyInProgressError
from .store import SqliteRunStore


class EffectIdempotencyStore:
    """Ensures external operations (e.g. PR creation, external dispatch) execute at most once."""

    def __init__(self, run_store: SqliteRunStore):
        self.store = run_store

    def execute_idempotent_effect(
        self,
        project_id: str,
        idempotency_key: str,
        effect_type: str,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> tuple[Any, bool]:
        """Execute external effect idempotently.

        Returns:
            (result, was_executed)
            was_executed is True on first execution, False if served from cached idempotent record.
        """
        now = datetime.now(UTC).isoformat()
        with self.store._connect() as conn:
            cursor = conn.execute(
                """
                SELECT status, result, error
                FROM external_effects
                WHERE project_id = ? AND idempotency_key = ? AND effect_type = ?
                """,
                (project_id, idempotency_key, effect_type),
            )
            row = cursor.fetchone()
            if row is not None:
                status = row["status"]
                if status == "completed":
                    cached = json.loads(row["result"]) if row["result"] else None
                    return cached, False
                if status == "pending":
                    raise EffectAlreadyInProgressError(
                        f"External effect {effect_type}:{idempotency_key} is already in progress"
                    )

            # Insert pending record
            conn.execute(
                """
                INSERT OR REPLACE INTO external_effects (
                    project_id, idempotency_key, effect_type,
                    status, result, error, created_at, completed_at
                ) VALUES (?, ?, ?, 'pending', NULL, NULL, ?, NULL)
                """,
                (project_id, idempotency_key, effect_type, now),
            )

        # Execute effect outside database lock
        try:
            res = fn(*args, **kwargs)
            res_json = json.dumps(res)
            completed_at = datetime.now(UTC).isoformat()
            with self.store._connect() as conn:
                conn.execute(
                    """
                    UPDATE external_effects
                    SET status = 'completed',
                        result = ?,
                        completed_at = ?
                    WHERE project_id = ? AND idempotency_key = ? AND effect_type = ?
                    """,
                    (res_json, completed_at, project_id, idempotency_key, effect_type),
                )
            return res, True
        except Exception as exc:
            completed_at = datetime.now(UTC).isoformat()
            with self.store._connect() as conn:
                conn.execute(
                    """
                    UPDATE external_effects
                    SET status = 'failed',
                        error = ?,
                        completed_at = ?
                    WHERE project_id = ? AND idempotency_key = ? AND effect_type = ?
                    """,
                    (str(exc), completed_at, project_id, idempotency_key, effect_type),
                )
            raise
