from __future__ import annotations

import time
from collections import deque
from pathlib import Path
from typing import Any

import sys


PERFORMANCE_ROOT = Path(__file__).resolve().parent
DEV_CORE_ROOT = PERFORMANCE_ROOT.parent
for path in [DEV_CORE_ROOT / "API", DEV_CORE_ROOT / "_archive" / "Database", DEV_CORE_ROOT / "Scripts"]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _p95_ms(samples: list[float]) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    index = min(len(ordered) - 1, int(len(ordered) * 0.95))
    return round(ordered[index] * 1000, 3)


class _TaskRepository:
    def __init__(self) -> None:
        from devcore_api.contracts import TaskContract

        self._tasks = [
            TaskContract(
                id="T-209",
                title="Load contract",
                status="active",
                mode="coding",
                steps_done=0,
                steps_total=1,
                project="devcore",
            )
        ]

    def list_tasks(self, project: str):
        return self._tasks


def _run_api_load(iterations: int) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from devcore_api import create_app

    client = TestClient(create_app(task_repository=_TaskRepository()))
    samples: list[float] = []

    for _ in range(iterations):
        for path in ["/api/v1/health", "/api/v1/contracts", "/api/v1/tasks?project=devcore"]:
            started = time.perf_counter()
            response = client.get(path)
            samples.append(time.perf_counter() - started)
            if response.status_code != 200:
                raise AssertionError(f"{path} returned {response.status_code}: {response.text}")

    return {"operations": iterations * 3, "p95_ms": _p95_ms(samples)}


def _run_sse_load(iterations: int) -> dict[str, Any]:
    import dashboard_api

    samples: list[float] = []
    for index in range(iterations):
        payload = {"schema_version": 1, "changed_keys": ["events"], "cursor": index}
        started = time.perf_counter()
        event = dashboard_api.format_sse_event("dashboard.delta", payload, event_id=f"evt-{index}")
        samples.append(time.perf_counter() - started)
        if not event.endswith(b"\n\n") or b"event: dashboard.delta\n" not in event:
            raise AssertionError("invalid SSE event format")

    return {"events": iterations, "p95_ms": _p95_ms(samples)}


class _RunRepository:
    def __init__(self, total: int) -> None:
        from devcore_api.worker import WorkerRun

        self._runs = deque(
            WorkerRun(id=f"run-{index}", task_id="T-209", status="queued", trace_id=f"trace-{index}")
            for index in range(total)
        )
        self.transitions: list[tuple[str, str]] = []

    def claim_next_queued(self):
        if not self._runs:
            return None
        return self._runs.popleft()

    def transition(self, run_id: str, action: str) -> None:
        self.transitions.append((run_id, action))


def _run_worker_load(iterations: int) -> dict[str, Any]:
    from devcore_api.worker import Worker

    repository = _RunRepository(iterations)
    worker = Worker(repository=repository, handler=lambda run: None)
    samples: list[float] = []

    for _ in range(iterations):
        started = time.perf_counter()
        result = worker.run_once()
        samples.append(time.perf_counter() - started)
        if result != "succeeded":
            raise AssertionError(f"worker returned {result}")

    return {"runs": iterations, "p95_ms": _p95_ms(samples)}


class _FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows


class _FakeSession:
    def __init__(self) -> None:
        self.statements: list[Any] = []
        self.rows = [
            {
                "id": "T-209",
                "title": "Load contract",
                "status": "active",
                "mode": "coding",
                "steps_done": 0,
                "steps_total": 1,
                "depends_on": None,
                "worktree": "main",
            }
        ]

    def execute(self, statement):
        self.statements.append(statement)
        return _FakeResult(self.rows)


def _run_db_load(iterations: int) -> dict[str, Any]:
    from devcore_db.repositories import SqlTaskRepository

    session = _FakeSession()
    repository = SqlTaskRepository(session)
    samples: list[float] = []

    for index in range(iterations):
        started = time.perf_counter()
        repository.create_task(project_id="devcore", task_id=f"T-{1000 + index}", title="Load task")
        samples.append(time.perf_counter() - started)

        started = time.perf_counter()
        tasks = repository.list_tasks(project="devcore")
        samples.append(time.perf_counter() - started)
        if not tasks or tasks[0].id != "T-209":
            raise AssertionError("repository list contract failed")

    return {"operations": iterations * 2, "p95_ms": _p95_ms(samples)}


def run_local_load_contract(
    *,
    api_iterations: int,
    sse_iterations: int,
    worker_iterations: int,
    db_iterations: int,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "api": _run_api_load(api_iterations),
        "sse": _run_sse_load(sse_iterations),
        "workers": _run_worker_load(worker_iterations),
        "db": _run_db_load(db_iterations),
    }
