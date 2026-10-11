"""Test suite for Lot L6: Transactional Outbox pattern, reliable publication,
idempotent consumer deduplication, exponential backoff, dead-letter queuing, and retention.

Strictly follows:
- Temporary isolated roots (DEVCORE_LOCAL_ROOT, DEVCORE_DATA_ROOT).
- Zero production data, Dropbox, or live index fixtures.
- Pure Python 3.13 verification.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from devcore_engine.persistence.models import metadata, outbox_messages, projects, tasks
from devcore_engine.persistence.outbox import (
    BackoffPolicy,
    IdempotentConsumer,
    OutboxMessage,
    OutboxPublisher,
    OutboxRepository,
)
from devcore_engine.persistence.repositories import SqlUnitOfWork


@pytest.fixture
def outbox_db(tmp_path):
    """Setup an isolated SQLite database containing tasks and outbox_messages tables."""
    db_file = tmp_path / "outbox_test.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"timeout": 30.0})

    ddl_statements = [
        """CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            workspace_id TEXT,
            name TEXT NOT NULL,
            root_path TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE tasks (
            task_uuid TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id),
            task_number INTEGER NOT NULL,
            legacy_id TEXT,
            title TEXT NOT NULL,
            mode TEXT DEFAULT 'coding',
            status TEXT DEFAULT 'todo',
            version INTEGER DEFAULT 1,
            steps_done INTEGER DEFAULT 0,
            steps_total INTEGER DEFAULT 1,
            depends_on_uuid TEXT,
            worktree TEXT,
            metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (project_id, task_number)
        )""",
        """CREATE TABLE outbox_messages (
            id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            payload TEXT NOT NULL DEFAULT '{}',
            idempotency_key TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            available_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP
        )""",
        "INSERT INTO projects (id, name, root_path) VALUES ('alpha', 'Alpha', '/alpha')",
    ]
    with engine.begin() as conn:
        for stmt in ddl_statements:
            conn.exec_driver_sql(stmt)

    session_factory = sessionmaker(bind=engine)
    return {"engine": engine, "session_factory": session_factory}


def test_unit_of_work_transactional_atomicity(outbox_db):
    """Verify Unit of Work commits or rolls back tasks and outbox events jointly."""
    session_factory = outbox_db["session_factory"]
    uow = SqlUnitOfWork(session_factory)

    # 1. Successful joint commit
    with uow:
        t = uow.tasks.create_task(project_id="alpha", title="Deploy Gateway")
        msg_id = uow.outbox.enqueue(
            topic="tasks.created",
            payload={"task_uuid": t["task_uuid"], "title": t["title"]},
            idempotency_key=f"created-{t['task_uuid']}",
        )
        uow.commit()

    # Verify both are committed
    with uow:
        assert uow.tasks.get_task(project_id="alpha", task_id=t["task_uuid"]) is not None
        outbox_msg = uow.outbox.get_message(msg_id)
        assert outbox_msg is not None
        assert outbox_msg.topic == "tasks.created"
        assert outbox_msg.status == "pending"

    # 2. Rollback on exception: neither task nor outbox message must persist
    with pytest.raises(RuntimeError, match="Simulated crash"):
        with uow:
            t_fail = uow.tasks.create_task(project_id="alpha", title="Doomed Task")
            uow.outbox.enqueue(
                topic="tasks.created",
                payload={"task_uuid": t_fail["task_uuid"]},
                idempotency_key=f"created-{t_fail['task_uuid']}",
            )
            raise RuntimeError("Simulated crash before commit")

    with uow:
        assert uow.tasks.get_task(project_id="alpha", task_id=t_fail["task_uuid"]) is None
        assert uow.outbox.get_message_by_idempotency_key(f"created-{t_fail['task_uuid']}") is None


def test_outbox_unique_idempotency_key(outbox_db):
    """Enforce unique idempotency keys in outbox_messages table."""
    session_factory = outbox_db["session_factory"]

    # First insert succeeds
    with session_factory() as session:
        repo = OutboxRepository(session)
        repo.enqueue(topic="events.item", payload={"val": 1}, idempotency_key="key-unique-1")
        session.commit()

    # Duplicate idempotency key fails with IntegrityError
    with session_factory() as session:
        repo = OutboxRepository(session)
        with pytest.raises(IntegrityError):
            repo.enqueue(topic="events.item", payload={"val": 2}, idempotency_key="key-unique-1")
            session.commit()


def test_claim_pending_respects_available_at_and_order(outbox_db):
    """claim_pending returns only ready messages (available_at <= now) in chronological order."""
    session_factory = outbox_db["session_factory"]
    now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=UTC)

    with session_factory() as session:
        repo = OutboxRepository(session)
        # Msg 1: ready now
        id1 = repo.enqueue(
            topic="t1", payload={}, idempotency_key="k1", available_at=now - timedelta(minutes=1)
        )
        # Msg 2: future (not ready)
        id2 = repo.enqueue(
            topic="t2", payload={}, idempotency_key="k2", available_at=now + timedelta(hours=1)
        )
        # Msg 3: ready now, slightly after Msg 1
        id3 = repo.enqueue(
            topic="t3", payload={}, idempotency_key="k3", available_at=now
        )
        session.commit()

    with session_factory() as session:
        repo = OutboxRepository(session)
        pending = repo.claim_pending(limit=10, now=now)
        assert len(pending) == 2
        assert pending[0].id == id1
        assert pending[1].id == id3


def test_idempotent_consumer_deduplication():
    """IdempotentConsumer executes handler only once per idempotency key."""
    seen_keys: set[str] = set()
    consumed_payloads: list[dict[str, Any]] = []

    def handle(msg: OutboxMessage):
        consumed_payloads.append(msg.payload)

    consumer = IdempotentConsumer(seen_keys=seen_keys, handler=handle)

    msg1 = OutboxMessage(id="1", topic="test", payload={"step": 1}, idempotency_key="evt-100")
    msg2 = OutboxMessage(id="2", topic="test", payload={"step": 2}, idempotency_key="evt-100")  # Duplicate key

    # First consumption
    res1 = consumer.consume(msg1)
    assert res1 == "processed"
    assert len(consumed_payloads) == 1
    assert "evt-100" in seen_keys

    # Duplicate consumption
    res2 = consumer.consume(msg2)
    assert res2 == "duplicate"
    assert len(consumed_payloads) == 1  # Handler was not called again


def test_outbox_retry_backoff_and_dead_letter(outbox_db):
    """Test exponential backoff retries and transition to dead_letter queue upon reaching max_attempts."""
    session_factory = outbox_db["session_factory"]
    now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=UTC)
    policy = BackoffPolicy(base_seconds=2.0, max_seconds=30.0, multiplier=2.0)

    with session_factory() as session:
        repo = OutboxRepository(session)
        mid = repo.enqueue(topic="err.topic", payload={"data": "test"}, idempotency_key="err-k1")
        session.commit()

    # Attempt 1: fail -> pending with backoff
    with session_factory() as session:
        repo = OutboxRepository(session)
        msg = repo.get_message(mid)
        status = repo.mark_failed(mid, attempts=msg.attempts, max_attempts=3, backoff_policy=policy, now=now)
        session.commit()
        assert status == "pending"

    with session_factory() as session:
        repo = OutboxRepository(session)
        msg = repo.get_message(mid)
        assert msg.attempts == 1
        assert msg.status == "pending"
        # Delay for attempt 0 was 2s: available_at should be now + 2s
        assert msg.available_at == now + timedelta(seconds=2.0)

    # Attempt 2: fail again -> pending with delay 4s
    now2 = now + timedelta(seconds=2.0)
    with session_factory() as session:
        repo = OutboxRepository(session)
        msg = repo.get_message(mid)
        status = repo.mark_failed(mid, attempts=msg.attempts, max_attempts=3, backoff_policy=policy, now=now2)
        session.commit()
        assert status == "pending"

    with session_factory() as session:
        repo = OutboxRepository(session)
        msg = repo.get_message(mid)
        assert msg.attempts == 2
        assert msg.status == "pending"
        assert msg.available_at == now2 + timedelta(seconds=4.0)

    # Attempt 3: reach max_attempts (3) -> dead_letter
    now3 = now2 + timedelta(seconds=4.0)
    with session_factory() as session:
        repo = OutboxRepository(session)
        msg = repo.get_message(mid)
        status = repo.mark_failed(mid, attempts=msg.attempts, max_attempts=3, backoff_policy=policy, now=now3)
        session.commit()
        assert status == "dead_letter"

    with session_factory() as session:
        repo = OutboxRepository(session)
        msg = repo.get_message(mid)
        assert msg.attempts == 3
        assert msg.status == "dead_letter"


def test_outbox_publisher_batch_lifecycle(outbox_db):
    """OutboxPublisher drains batches, marks processed, and handles errors with DLQ."""
    session_factory = outbox_db["session_factory"]
    now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=UTC)

    # Enqueue 3 messages
    with session_factory() as session:
        repo = OutboxRepository(session)
        repo.enqueue(topic="success.1", payload={"id": 1}, idempotency_key="batch-1", available_at=now)
        repo.enqueue(topic="fail.2", payload={"fail": True}, idempotency_key="batch-2", available_at=now)
        repo.enqueue(topic="success.3", payload={"id": 3}, idempotency_key="batch-3", available_at=now)
        session.commit()

    seen_keys: set[str] = set()

    def handler(msg: OutboxMessage):
        if msg.payload.get("fail"):
            raise ValueError("Consumer delivery error")

    consumer = IdempotentConsumer(seen_keys=seen_keys, handler=handler)

    with session_factory() as session:
        repo = OutboxRepository(session)
        publisher = OutboxPublisher(repo, consumer, max_attempts=2)
        stats = publisher.publish_batch(limit=10, now=now)
        session.commit()

    assert stats["claimed"] == 3
    assert stats["processed"] == 2
    assert stats["failed"] == 1
    assert stats["dead_letter"] == 0

    # Verify message statuses in database
    with session_factory() as session:
        repo = OutboxRepository(session)
        m1 = repo.get_message_by_idempotency_key("batch-1")
        m2 = repo.get_message_by_idempotency_key("batch-2")
        m3 = repo.get_message_by_idempotency_key("batch-3")
        assert m1.status == "processed"
        assert m1.processed_at is not None
        assert m3.status == "processed"
        assert m2.status == "pending"
        assert m2.attempts == 1


def test_purge_processed_retention(outbox_db):
    """Verify purge_processed deletes expired processed messages while preserving pending and DLQ."""
    session_factory = outbox_db["session_factory"]
    now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=UTC)

    with session_factory() as session:
        repo = OutboxRepository(session)
        # Processed 3 days ago (expired with 1 day retention)
        id_expired = repo.enqueue(topic="t.old", payload={}, idempotency_key="old-1")
        repo.mark_processed(id_expired, now=now - timedelta(days=3))

        # Processed 10 minutes ago (not expired)
        id_recent = repo.enqueue(topic="t.recent", payload={}, idempotency_key="recent-1")
        repo.mark_processed(id_recent, now=now - timedelta(minutes=10))

        # Pending message
        id_pending = repo.enqueue(topic="t.pending", payload={}, idempotency_key="pend-1")

        session.commit()

    with session_factory() as session:
        repo = OutboxRepository(session)
        deleted = repo.purge_processed(retention_seconds=86400.0, now=now)  # 24h retention
        session.commit()
        assert deleted == 1

    with session_factory() as session:
        repo = OutboxRepository(session)
        assert repo.get_message(id_expired) is None
        assert repo.get_message(id_recent) is not None
        assert repo.get_message(id_pending) is not None
