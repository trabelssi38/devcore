import sys
from pathlib import Path


API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


class FakeRunRepository:
    def __init__(self, run=None):
        self.run = run
        self.transitions = []

    def claim_next_queued(self):
        claimed = self.run
        self.run = None
        return claimed

    def transition(self, run_id: str, action: str):
        self.transitions.append((run_id, action))


def test_worker_executes_claimed_run_successfully() -> None:
    from devcore_api.worker import Worker, WorkerRun

    repository = FakeRunRepository(WorkerRun(id="run-1", task_id="T-168", status="queued"))
    executed = []

    result = Worker(repository=repository, handler=lambda run: executed.append(run.id)).run_once()

    assert result == "succeeded"
    assert executed == ["run-1"]
    assert repository.transitions == [("run-1", "start"), ("run-1", "succeed")]


def test_worker_marks_run_failed_when_handler_raises() -> None:
    from devcore_api.worker import Worker, WorkerRun

    repository = FakeRunRepository(WorkerRun(id="run-2", task_id="T-168", status="queued"))

    def fail(_run):
        raise RuntimeError("boom")

    result = Worker(repository=repository, handler=fail).run_once()

    assert result == "failed"
    assert repository.transitions == [("run-2", "start"), ("run-2", "fail")]


def test_worker_noops_without_queued_run() -> None:
    from devcore_api.worker import Worker

    repository = FakeRunRepository()

    assert Worker(repository=repository, handler=lambda run: None).run_once() == "idle"
    assert repository.transitions == []
