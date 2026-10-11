"""Transactional Outbox pattern repository, idempotent consumer, and publisher.

Ensures at-least-once delivery with exactly-once consumer deduplication,
exponential backoff, dead-letter queuing, and configurable retention.
"""

from __future__ import annotations

from collections.abc import Callable, MutableSet
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import json
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import delete, func, insert, select, update

from .models import outbox_messages

ConsumeResult = Literal["processed", "duplicate"]


@dataclass(frozen=True)
class OutboxMessage:
    """Represents a discrete domain event pending publication or delivered."""

    id: str
    topic: str
    payload: dict[str, Any]
    idempotency_key: str
    status: str = "pending"
    attempts: int = 0
    created_at: datetime | None = None
    available_at: datetime | None = None
    processed_at: datetime | None = None


@dataclass(frozen=True)
class BackoffPolicy:
    """Configurable exponential backoff policy for failed outbox message deliveries."""

    base_seconds: float = 2.0
    max_seconds: float = 300.0
    multiplier: float = 2.0

    def delay_for_attempt(self, attempt: int) -> timedelta:
        """Calculate backoff delay for the given retry attempt."""
        delay = min(self.base_seconds * (self.multiplier ** max(0, attempt)), self.max_seconds)
        return timedelta(seconds=delay)


class OutboxRepository:
    """Transactional repository managing outbox_messages in SQLAlchemy session."""

    def __init__(self, session: Any) -> None:
        self.session = session

    def enqueue(
        self,
        *,
        topic: str,
        payload: dict[str, Any],
        idempotency_key: str,
        message_id: str | None = None,
        available_at: datetime | None = None,
    ) -> str:
        """Enqueue an event in outbox within the caller's active database transaction."""
        mid = message_id or str(uuid4())
        now = datetime.now(UTC)
        avail = available_at or now

        stmt = insert(outbox_messages).values(
            id=mid,
            topic=topic,
            payload=payload,
            idempotency_key=idempotency_key,
            status="pending",
            attempts=0,
            created_at=now,
            available_at=avail,
            processed_at=None,
        )
        self.session.execute(stmt)
        return mid

    def get_message(self, message_id: str) -> OutboxMessage | None:
        """Retrieve a message by id."""
        stmt = select(outbox_messages).where(outbox_messages.c.id == message_id)
        res = self.session.execute(stmt)
        if hasattr(res, "mappings"):
            row = res.mappings().first()
            if row:
                return self._row_to_message(row)
        return None

    def get_message_by_idempotency_key(self, idempotency_key: str) -> OutboxMessage | None:
        """Retrieve a message by its unique idempotency key."""
        stmt = select(outbox_messages).where(outbox_messages.c.idempotency_key == idempotency_key)
        res = self.session.execute(stmt)
        if hasattr(res, "mappings"):
            row = res.mappings().first()
            if row:
                return self._row_to_message(row)
        return None

    def claim_pending(self, *, limit: int = 50, now: datetime | None = None) -> list[OutboxMessage]:
        """Fetch pending messages ready for delivery (available_at <= now)."""
        current_time = now or datetime.now(UTC)
        stmt = (
            select(outbox_messages)
            .where(
                (outbox_messages.c.status == "pending")
                & (outbox_messages.c.available_at <= current_time)
            )
            .order_by(outbox_messages.c.created_at.asc())
            .limit(max(1, limit))
        )
        res = self.session.execute(stmt)
        if hasattr(res, "mappings"):
            rows = res.mappings().all()
            return [self._row_to_message(r) for r in rows]
        return []

    def mark_processed(self, message_id: str, *, now: datetime | None = None) -> bool:
        """Mark a message as successfully processed."""
        current_time = now or datetime.now(UTC)
        stmt = (
            update(outbox_messages)
            .where(outbox_messages.c.id == message_id)
            .values(
                status="processed",
                processed_at=current_time,
            )
        )
        res = self.session.execute(stmt)
        rowcount = getattr(res, "rowcount", 0)
        return rowcount > 0

    def mark_failed(
        self,
        message_id: str,
        *,
        attempts: int,
        max_attempts: int = 5,
        backoff_policy: BackoffPolicy | None = None,
        now: datetime | None = None,
    ) -> str:
        """Record a delivery failure, apply exponential backoff, or move to dead_letter."""
        policy = backoff_policy or BackoffPolicy()
        current_time = now or datetime.now(UTC)
        next_attempt = attempts + 1

        if next_attempt >= max_attempts:
            new_status = "dead_letter"
            next_avail = current_time
        else:
            new_status = "pending"
            next_avail = current_time + policy.delay_for_attempt(attempts)

        stmt = (
            update(outbox_messages)
            .where(outbox_messages.c.id == message_id)
            .values(
                status=new_status,
                attempts=next_attempt,
                available_at=next_avail,
            )
        )
        self.session.execute(stmt)
        return new_status

    def purge_processed(self, *, retention_seconds: float = 86400.0, now: datetime | None = None) -> int:
        """Purge successfully processed messages older than the retention threshold."""
        current_time = now or datetime.now(UTC)
        cutoff = current_time - timedelta(seconds=max(0.0, retention_seconds))
        stmt = (
            delete(outbox_messages)
            .where(
                (outbox_messages.c.status == "processed")
                & (outbox_messages.c.processed_at <= cutoff)
            )
        )
        res = self.session.execute(stmt)
        return getattr(res, "rowcount", 0) or 0

    @staticmethod
    def _parse_dt(val: Any) -> datetime | None:
        if val is None:
            return None
        if isinstance(val, str):
            try:
                val = datetime.fromisoformat(val)
            except Exception:
                return None
        if isinstance(val, datetime) and val.tzinfo is None:
            val = val.replace(tzinfo=UTC)
        return val

    @staticmethod
    def _row_to_message(row: Any) -> OutboxMessage:
        d = dict(row)
        payload = d.get("payload")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        return OutboxMessage(
            id=str(d["id"]),
            topic=str(d["topic"]),
            payload=payload if isinstance(payload, dict) else {},
            idempotency_key=str(d["idempotency_key"]),
            status=str(d.get("status", "pending")),
            attempts=int(d.get("attempts", 0)),
            created_at=OutboxRepository._parse_dt(d.get("created_at")),
            available_at=OutboxRepository._parse_dt(d.get("available_at")),
            processed_at=OutboxRepository._parse_dt(d.get("processed_at")),
        )


class IdempotentConsumer:
    """Guarantees exactly-once consumer execution via seen idempotency keys."""

    def __init__(self, *, seen_keys: MutableSet[str], handler: Callable[[OutboxMessage], None]) -> None:
        self.seen_keys = seen_keys
        self.handler = handler

    def consume(self, message: OutboxMessage) -> ConsumeResult:
        """Process message if not seen; return 'duplicate' if key was already processed."""
        if message.idempotency_key in self.seen_keys:
            return "duplicate"
        self.handler(message)
        self.seen_keys.add(message.idempotency_key)
        return "processed"


class OutboxPublisher:
    """Drives publication batch draining with backoff and dead-letter handling."""

    def __init__(
        self,
        repository: OutboxRepository,
        consumer: IdempotentConsumer,
        *,
        max_attempts: int = 5,
        backoff_policy: BackoffPolicy | None = None,
    ) -> None:
        self.repository = repository
        self.consumer = consumer
        self.max_attempts = max_attempts
        self.backoff_policy = backoff_policy or BackoffPolicy()

    def publish_batch(self, *, limit: int = 50, now: datetime | None = None) -> dict[str, int]:
        """Claim pending messages and dispatch to consumer with retry & DLQ handling."""
        current_time = now or datetime.now(UTC)
        messages = self.repository.claim_pending(limit=limit, now=current_time)

        stats = {
            "claimed": len(messages),
            "processed": 0,
            "duplicate": 0,
            "failed": 0,
            "dead_letter": 0,
        }

        for msg in messages:
            try:
                result = self.consumer.consume(msg)
                self.repository.mark_processed(msg.id, now=current_time)
                if result == "processed":
                    stats["processed"] += 1
                else:
                    stats["duplicate"] += 1
            except Exception:
                stats["failed"] += 1
                final_status = self.repository.mark_failed(
                    msg.id,
                    attempts=msg.attempts,
                    max_attempts=self.max_attempts,
                    backoff_policy=self.backoff_policy,
                    now=current_time,
                )
                if final_status == "dead_letter":
                    stats["dead_letter"] += 1

        return stats
