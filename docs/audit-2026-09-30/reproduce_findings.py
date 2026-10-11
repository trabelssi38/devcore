"""Reproductions d'audit sur stockage temporaire, sans services externes.

Depuis la racine : python docs/audit-2026-09-30/reproduce_findings.py
Sortie descriptive : ce script constate les comportements, ce n'est pas un
test de non-regression qui validerait les comportements defectueux.
"""
import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch


def main():
    root = Path(__file__).resolve().parents[2]
    sys.path[:0] = [str(root / "DEV_CORE"), str(root / "DEV_CORE/API"), str(root / "DEV_CORE/Scripts")]
    results = {}
    with tempfile.TemporaryDirectory(prefix="devcore_audit_") as td:
        os.environ.update(DEVCORE_DATA_ROOT=td, DEVCORE_LOCAL_ROOT=td,
                          DEVCORE_PLATFORM_ROOT=str(root / "DEV_CORE"))
        os.environ.pop("DEVCORE_ACTIVE_PROJECT_NAME", None)
        from devcore_engine.services.tasks import TaskService
        from devcore_engine.lifecycle.session import SessionManager
        from devcore_api.worker import Worker, WorkerRun

        ts = TaskService(Path(td))
        try:
            ts.add_task("Task A", project_id="audit_a")
            ts.add_task("Task B", project_id="audit_b")
            ts.edit_task("T-01", title="Edit intended for A", project_id="audit_a")
            results["cross_project_edit"] = [dict(r) for r in ts.conn.execute(
                "SELECT id,project_id,title FROM tasks ORDER BY project_id")]
            a, b = SessionManager(ts.conn), SessionManager(ts.conn)
            a.set_active_project("audit_a")
            b.set_active_project("audit_b")
            results["session_a_after_b_switch"] = a.get_active_project()
            try:
                ts.conn.execute("INSERT INTO runs(id,project_id,task_id) VALUES('r','audit_a','T-01')")
                results["run_foreign_key"] = "insert accepted"
            except sqlite3.Error as exc:
                results["run_foreign_key"] = str(exc)
        finally:
            ts.conn.close()

        class Repository:
            def claim_next_queued(self):
                return WorkerRun(id="r", task_id="t", status="queued")

            def transition(self, *args):
                pass

        start = time.perf_counter()
        result = Worker(repository=Repository(), handler=lambda _: time.sleep(0.2),
                        timeout_seconds=0.02).run_once()
        results["worker_timeout"] = {"configured_s": 0.02,
                                     "elapsed_s": round(time.perf_counter() - start, 3),
                                     "result": result}

        import dashboard_api as dashboard
        from starlette.requests import Request

        async def probe_event_loop():
            fired, observed = asyncio.Event(), []

            async def heartbeat():
                await fired.wait()
                observed.append(time.perf_counter())

            def slow_refresh():
                fired.set()
                time.sleep(0.2)
                return {}

            request = Request({"type": "http", "method": "POST", "path": "/api/refresh", "headers": []})
            beat = asyncio.create_task(heartbeat())
            await asyncio.sleep(0)
            started = time.perf_counter()
            with patch.object(dashboard, "check_auth", return_value=True), \
                 patch.object(dashboard, "check_csrf", return_value=True), \
                 patch.object(dashboard, "refresh_dashboard_payload_cache", side_effect=slow_refresh):
                await dashboard.post_refresh_route(request)
            await beat
            return {"simulated_sync_work_s": 0.2,
                    "heartbeat_delay_s": round(observed[0] - started, 3)}

        results["event_loop_block"] = asyncio.run(probe_event_loop())
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
