from __future__ import annotations

from .contracts import RunStatus


RunAction = str


class InvalidRunTransition(ValueError):
    pass


class RunStateMachine:
    TERMINAL_STATES: set[str] = {"succeeded", "failed", "cancelled", "timed_out"}
    ACTIVE_STATES: set[str] = {"queued", "running"}
    TRANSITIONS: dict[tuple[str, RunAction], RunStatus] = {
        ("queued", "start"): "running",
        ("queued", "cancel"): "cancelled",
        ("running", "succeed"): "succeeded",
        ("running", "fail"): "failed",
        ("running", "timeout"): "timed_out",
        ("running", "cancel"): "cancelled",
    }

    def transition(self, status: RunStatus, action: RunAction) -> RunStatus:
        next_status = self.TRANSITIONS.get((status, action))
        if next_status is None:
            raise InvalidRunTransition(f"Invalid run transition: {status} --{action}--> ?")
        return next_status

    def is_terminal(self, status: RunStatus) -> bool:
        return status in self.TERMINAL_STATES

    def is_active(self, status: RunStatus) -> bool:
        return status in self.ACTIVE_STATES
