from datetime import UTC, datetime, timedelta
import sys
from pathlib import Path


DATABASE_ROOT = Path(__file__).resolve().parent
API_ROOT = DATABASE_ROOT.parent / "API"
for path in [DATABASE_ROOT, API_ROOT]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


class FakeSession:
    def __init__(self):
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)


def test_backoff_policy_is_exponential_and_capped() -> None:
    from devcore_db.outbox import BackoffPolicy

    policy = BackoffPolicy(base_seconds=5, max_seconds=60)

    assert policy.delay_for_attempt(0) == timedelta(seconds=5)
    assert policy.delay_for_attempt(1) == timedelta(seconds=10)
    assert policy.delay_for_attempt(4) == timedelta(seconds=60)


def test_outbox_repository_schedules_retry_before_dead_letter() -> None:
    from devcore_db.outbox import BackoffPolicy, OutboxRepository

    session = FakeSession()
    now = datetime(2026, 7, 12, 17, 0, tzinfo=UTC)

    OutboxRepository(session).mark_failed(
        message_id="msg-1",
        attempts=1,
        max_attempts=3,
        backoff_policy=BackoffPolicy(base_seconds=10),
        now=now,
    )

    statement = session.statements[0]
    assert statement.is_update
    assert statement.table.name == "outbox_messages"


def test_outbox_repository_dead_letters_after_max_attempts() -> None:
    from devcore_db.outbox import BackoffPolicy, OutboxRepository

    session = FakeSession()

    OutboxRepository(session).mark_failed(
        message_id="msg-1",
        attempts=3,
        max_attempts=3,
        backoff_policy=BackoffPolicy(base_seconds=10),
    )

    statement = session.statements[0]
    assert statement.is_update
    assert statement.table.name == "outbox_messages"


def test_worker_timeout_maps_to_timed_out_transition() -> None:
    from devcore_api.worker import Worker, WorkerRun

    class TimeoutRepository:
        def __init__(self):
            self.transitions = []

        def claim_next_queued(self):
            return WorkerRun(id="run-timeout", task_id="T-170", status="queued")

        def transition(self, run_id: str, action: str):
            self.transitions.append((run_id, action))

    repository = TimeoutRepository()

    result = Worker(repository=repository, handler=lambda run: None, timeout_seconds=0).run_once()

    assert result == "timed_out"
    assert repository.transitions == [("run-timeout", "start"), ("run-timeout", "timeout")]
