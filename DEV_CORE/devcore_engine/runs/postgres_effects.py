"""Project-scoped PostgreSQL deduplication of external effects."""

from __future__ import annotations

from collections.abc import Callable
import json
from typing import Any

from .models import EffectAlreadyInProgressError
from .postgres_store import PostgresRunStore, _json


class PostgresEffectIdempotencyStore:
    def __init__(self, run_store: PostgresRunStore):
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
        if not idempotency_key or not effect_type:
            raise ValueError("Effect type and idempotency key are required")
        with self.store._transaction(project_id) as cursor:
            cursor.execute("""INSERT INTO external_effects
                (project_id, idempotency_key, effect_type, status)
                VALUES (%s, %s, %s, 'pending')
                ON CONFLICT (project_id, idempotency_key, effect_type)
                DO UPDATE SET status='pending', result=NULL, error=NULL,
                    completed_at=NULL
                WHERE external_effects.status='failed'
                RETURNING status""", (project_id, idempotency_key, effect_type))
            claimed = cursor.fetchone() is not None
            if not claimed:
                cursor.execute("""SELECT status, result FROM external_effects
                    WHERE project_id=%s AND idempotency_key=%s AND effect_type=%s""",
                    (project_id, idempotency_key, effect_type))
                current = cursor.fetchone()
                if current is None:
                    raise RuntimeError("Effect conflict was not readable under project RLS")
                if current[0] == "completed":
                    return _json(current[1], None), False
                raise EffectAlreadyInProgressError(
                    f"External effect {effect_type}:{idempotency_key} is already in progress"
                )

        try:
            result = fn(*args, **kwargs)
            encoded = json.dumps(result)
        except Exception as exc:
            with self.store._transaction(project_id) as cursor:
                cursor.execute("""UPDATE external_effects SET status='failed', error=%s,
                    completed_at=now() WHERE project_id=%s AND idempotency_key=%s
                    AND effect_type=%s AND status='pending'""",
                    (str(exc), project_id, idempotency_key, effect_type))
                if cursor.rowcount != 1:
                    raise RuntimeError("Effect claim was lost while recording failure") from exc
            raise

        with self.store._transaction(project_id) as cursor:
            cursor.execute("""UPDATE external_effects SET status='completed', result=%s::jsonb,
                completed_at=now() WHERE project_id=%s AND idempotency_key=%s
                AND effect_type=%s AND status='pending'""",
                (encoded, project_id, idempotency_key, effect_type))
            if cursor.rowcount != 1:
                raise RuntimeError("Effect claim was lost while recording completion")
        return result, True
