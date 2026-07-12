import sys
from pathlib import Path


API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def test_run_state_machine_supports_pause_resume_cancel() -> None:
    from devcore_api.run_state import RunStateMachine

    machine = RunStateMachine()

    assert machine.transition("running", "pause") == "paused"
    assert machine.transition("paused", "resume") == "running"
    assert machine.transition("paused", "cancel") == "cancelled"
    assert machine.is_active("paused") is False


def test_worker_skips_paused_run_and_can_resume_after_restart() -> None:
    from devcore_api.worker import Worker, WorkerRun

    class Repository:
        def __init__(self):
            self.transitions = []
            self.resume_called = False

        def claim_next_queued(self):
            return WorkerRun(id="run-paused", task_id="T-171", status="paused")

        def transition(self, run_id: str, action: str):
            self.transitions.append((run_id, action))

        def resume_interrupted(self):
            self.resume_called = True
            return 1

    repository = Repository()

    assert Worker(repository=repository, handler=lambda run: None).run_once() == "paused"
    assert repository.transitions == []
    assert Worker(repository=repository, handler=lambda run: None).resume_after_restart() == 1
    assert repository.resume_called is True
