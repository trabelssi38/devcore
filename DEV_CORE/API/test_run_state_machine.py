import sys
from pathlib import Path


API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def test_run_state_machine_allows_expected_transitions() -> None:
    from devcore_api.run_state import RunStateMachine

    machine = RunStateMachine()

    assert machine.transition("queued", "start") == "running"
    assert machine.transition("running", "succeed") == "succeeded"
    assert machine.transition("running", "fail") == "failed"
    assert machine.transition("running", "timeout") == "timed_out"
    assert machine.transition("queued", "cancel") == "cancelled"
    assert machine.transition("running", "cancel") == "cancelled"


def test_run_state_machine_rejects_invalid_transitions() -> None:
    from devcore_api.run_state import InvalidRunTransition, RunStateMachine

    machine = RunStateMachine()

    for status in ["succeeded", "failed", "cancelled", "timed_out"]:
        try:
            machine.transition(status, "start")
        except InvalidRunTransition as exc:
            assert status in str(exc)
        else:
            raise AssertionError(f"{status} should be terminal")


def test_run_state_machine_exposes_terminal_and_active_states() -> None:
    from devcore_api.run_state import RunStateMachine

    machine = RunStateMachine()

    assert machine.is_active("queued") is True
    assert machine.is_active("running") is True
    assert machine.is_terminal("succeeded") is True
    assert machine.is_terminal("failed") is True
    assert machine.is_terminal("cancelled") is True
    assert machine.is_terminal("timed_out") is True
