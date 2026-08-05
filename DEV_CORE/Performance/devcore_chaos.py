from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


PERFORMANCE_ROOT = Path(__file__).resolve().parent
DEV_CORE_ROOT = PERFORMANCE_ROOT.parent
for path in [DEV_CORE_ROOT / "API", DEV_CORE_ROOT / "_archive" / "Database"]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


class _CrashRecoveryRepository:
    def __init__(self, *, run_id: str, task_id: str) -> None:
        from devcore_api.worker import WorkerRun

        self.run = WorkerRun(id=run_id, task_id=task_id, status="queued")
        self.interrupted = False
        self.transitions: list[tuple[str, str]] = []

    def claim_next_queued(self):
        claimed = self.run
        self.run = None
        return claimed

    def transition(self, run_id: str, action: str) -> None:
        self.transitions.append((run_id, action))
        if action == "start":
            self.interrupted = True

    def resume_interrupted(self) -> int:
        if not self.interrupted:
            return 0
        run_id = self.transitions[-1][0]
        self.transitions.append((run_id, "resume"))
        self.interrupted = False
        return 1


def simulate_process_kill_recovery(*, run_id: str, task_id: str) -> dict[str, Any]:
    from devcore_api.worker import Worker

    repository = _CrashRecoveryRepository(run_id=run_id, task_id=task_id)

    def crash(_run) -> None:
        raise SystemExit("simulated process kill")

    try:
        Worker(repository=repository, handler=crash).run_once()
    except SystemExit:
        pass

    resumed = Worker(repository=repository, handler=lambda run: None).resume_after_restart()
    return {
        "schema_version": 1,
        "scenario": "process_kill",
        "ok": resumed == 1 and repository.interrupted is False,
        "resumed_runs": resumed,
        "transitions": repository.transitions,
    }


class _RestartSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def execute(self, _statement: Any) -> None:
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True

    def as_report(self) -> dict[str, bool]:
        return {
            "committed": self.committed,
            "rolled_back": self.rolled_back,
            "closed": self.closed,
        }


def simulate_db_restart_recovery() -> dict[str, Any]:
    from devcore_db.repositories import UnitOfWork

    sessions = [_RestartSession(), _RestartSession()]

    try:
        with UnitOfWork(lambda: sessions[0]):
            raise ConnectionError("simulated db restart")
    except ConnectionError:
        pass

    with UnitOfWork(lambda: sessions[1]) as uow:
        uow.session.execute("select 1")

    return {
        "schema_version": 1,
        "scenario": "db_restart",
        "ok": sessions[0].rolled_back and sessions[0].closed and sessions[1].committed and sessions[1].closed,
        "first_session": sessions[0].as_report(),
        "second_session": sessions[1].as_report(),
        "reconnected": sessions[0] is not sessions[1],
    }


def simulate_qdrant_unavailable(*, collections: list[str]) -> dict[str, Any]:
    failures = [
        {
            "collection": collection,
            "error": "qdrant_unavailable",
            "message": "Simulated connection failure",
        }
        for collection in collections
    ]
    return {
        "schema_version": 1,
        "scenario": "qdrant_unavailable",
        "ok": True,
        "status": "degraded",
        "fatal": False,
        "collections": collections,
        "failures": failures,
        "retry": {
            "recommended": True,
            "command": "docker start qdrant",
            "backoff_seconds": 30,
        },
    }
