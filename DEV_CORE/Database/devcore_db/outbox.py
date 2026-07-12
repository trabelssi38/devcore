from __future__ import annotations

from collections.abc import Callable, MutableSet
from dataclasses import dataclass
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import insert, select

from .models import outbox_messages


@dataclass(frozen=True)
class OutboxMessage:
    id: str
    topic: str
    payload: dict[str, Any]
    idempotency_key: str


class OutboxRepository:
    def __init__(self, session):
        self.session = session

    def enqueue(self, *, topic: str, payload: dict[str, Any], idempotency_key: str) -> str:
        message_id = str(uuid4())
        statement = insert(outbox_messages).values(
            id=message_id,
            topic=topic,
            payload=payload,
            idempotency_key=idempotency_key,
            status="pending",
        )
        self.session.execute(statement)
        return message_id

    def claim_pending(self, *, limit: int) -> list[OutboxMessage]:
        statement = (
            select(
                outbox_messages.c.id,
                outbox_messages.c.topic,
                outbox_messages.c.payload,
                outbox_messages.c.idempotency_key,
            )
            .where(outbox_messages.c.status == "pending")
            .order_by(outbox_messages.c.created_at.asc())
            .limit(limit)
        )
        rows = self.session.execute(statement).mappings().all()
        return [OutboxMessage(**dict(row)) for row in rows]


ConsumeResult = Literal["processed", "duplicate"]


class IdempotentConsumer:
    def __init__(self, *, seen_keys: MutableSet[str], handler: Callable[[OutboxMessage], None]):
        self.seen_keys = seen_keys
        self.handler = handler

    def consume(self, message: OutboxMessage) -> ConsumeResult:
        if message.idempotency_key in self.seen_keys:
            return "duplicate"
        self.handler(message)
        self.seen_keys.add(message.idempotency_key)
        return "processed"
