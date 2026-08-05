import sys
from pathlib import Path


DATABASE_ROOT = Path(__file__).resolve().parent
if str(DATABASE_ROOT) not in sys.path:
    sys.path.insert(0, str(DATABASE_ROOT))


class FakeResult:
    def __init__(self, rows=None):
        self.rows = rows or []

    def mappings(self):
        return self

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        return FakeResult(self.rows)


def test_outbox_table_is_declared_in_metadata() -> None:
    from devcore_db.models import metadata

    table = metadata.tables["outbox_messages"]

    assert table.c.id.primary_key is True
    assert table.c.idempotency_key.unique is True
    assert table.c.payload.type.__class__.__name__ == "JSONB"
    assert "idx_outbox_messages_status_created" in {index.name for index in table.indexes}


def test_outbox_repository_enqueues_and_claims_messages() -> None:
    from devcore_db.outbox import OutboxRepository

    session = FakeSession(
        rows=[
            {
                "id": "msg-1",
                "topic": "run.events",
                "payload": {"run_id": "run-1"},
                "idempotency_key": "run-1:succeeded",
            }
        ]
    )
    repository = OutboxRepository(session)

    repository.enqueue(topic="run.events", payload={"run_id": "run-1"}, idempotency_key="run-1:succeeded")
    messages = repository.claim_pending(limit=10)

    assert session.statements[0].is_insert
    assert session.statements[0].table.name == "outbox_messages"
    assert messages[0].id == "msg-1"
    assert messages[0].idempotency_key == "run-1:succeeded"


def test_idempotent_consumer_skips_duplicate_messages() -> None:
    from devcore_db.outbox import IdempotentConsumer, OutboxMessage

    handled = []
    seen = set()
    consumer = IdempotentConsumer(seen_keys=seen, handler=lambda message: handled.append(message.id))
    message = OutboxMessage(
        id="msg-1",
        topic="run.events",
        payload={"run_id": "run-1"},
        idempotency_key="run-1:succeeded",
    )

    assert consumer.consume(message) == "processed"
    assert consumer.consume(message) == "duplicate"
    assert handled == ["msg-1"]
    assert seen == {"run-1:succeeded"}
