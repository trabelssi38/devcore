"""Persistent, fail-closed launch budget for the Windows global stack task.

The Task Scheduler time trigger may run forever, but no more than three failed
launches in thirty minutes may start the supervisor. Exhaustion is latched until
an operator explicitly resets it. ``IgnoreNew`` on the task serializes callers.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import time


MAX_FAILURES = 3
WINDOW_SECONDS = 30 * 60
STABLE_RUN_SECONDS = 30 * 60


class RestartBudget:
    def __init__(self, runtime: Path):
        if not runtime.is_absolute():
            raise ValueError("Absolute runtime directory required")
        self.path = runtime / "restart-budget.json"

    def read(self) -> dict:
        if not self.path.exists():
            return {"version": 1, "failures": [], "exhausted": False}
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if (not isinstance(value, dict) or value.get("version") != 1
                or type(value.get("exhausted")) is not bool
                or not isinstance(value.get("failures"), list)
                or any(type(item) not in (int, float) or not math.isfinite(item)
                       or item < 0 for item in value["failures"])):
            raise ValueError("Invalid restart budget state; launch refused")
        return value

    def _write(self, value: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
        deadline = time.monotonic() + 5
        while True:
            try:
                os.replace(temporary, self.path)
                return
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.05)

    def allow(self) -> bool:
        return not self.read()["exhausted"]

    def record_failure(self, *, started_at: float, finished_at: float,
                       phase: str, exit_code: int | None = None) -> dict:
        if not 0 <= started_at <= finished_at or not isinstance(phase, str):
            raise ValueError("Invalid restart failure evidence")
        value = self.read()
        if finished_at - started_at >= STABLE_RUN_SECONDS:
            failures = []
        else:
            failures = [item for item in value["failures"]
                        if item > finished_at or finished_at - item <= WINDOW_SECONDS]
        failures.append(finished_at)
        exhausted = value["exhausted"] or len(failures) >= MAX_FAILURES
        value.update({"failures": failures, "exhausted": exhausted, "last_phase": phase,
                      "last_exit_code": exit_code, "last_failure_at": finished_at})
        if exhausted and "alert" not in value:
            value["alert"] = {"code": "global_restart_budget_exhausted",
                              "requires_operator": True, "raised_at": finished_at}
        self._write(value)
        return value

    def record_success(self) -> None:
        value = self.read()
        value.update({"failures": [], "exhausted": False})
        value.pop("alert", None)
        self._write(value)

    def reset(self, *, reason: str, at: float) -> None:
        if not isinstance(reason, str) or not 3 <= len(reason.strip()) <= 200:
            raise ValueError("An operator reason of 3-200 characters is required")
        value = {"version": 1, "failures": [], "exhausted": False,
                 "reset_at": at, "reset_reason": reason.strip()}
        self._write(value)
