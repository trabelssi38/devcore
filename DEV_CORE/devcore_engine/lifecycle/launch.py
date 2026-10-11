"""
launch.py -- DEV_CORE Platform Launcher (Python Native)
Replaces launch.ps1 by orchestrating zero-Docker platform bootstrapper.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import socket
import sqlite3
import subprocess
import time

from typing import Any, Dict, Optional

from devcore_engine.db import connect_db, init_db
from devcore_engine.context import RequestContext
from devcore_engine.services.events import EventBus
from devcore_engine.lifecycle.session import SessionManager
from devcore_engine.services.tasks import _validate_project_id


def check_port(host: str, port: int, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


class PlatformLauncher:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or init_db()
        self.event_bus = EventBus(self.conn)
        self.session_manager = SessionManager(self.conn)

    def launch(self, project_id: str, client: str = "auto") -> Dict[str, Any]:
        context = RequestContext(project_id=_validate_project_id(project_id))
        project_id = context.project_id
        start_time = time.time()

        # Migrations require an explicit import command; startup must not replay Dropbox JSON.
        # Check Native Services & Auto-Heal via SystemWatcher.
        from devcore_engine.infra.system_watcher import SystemWatcher
        watcher = SystemWatcher(self.conn)
        watch_result = watcher.audit_and_heal()

        dashboard_up = watch_result["services"].get("dashboard_api", False)
        router_up = watch_result["services"].get("gemini_router", False)
        headroom_up = watch_result["services"].get("headroom_proxy", False)



        # 3. Initialize Session Context
        session_info = self.session_manager.start_session(context)

        duration = time.time() - start_time

        # 4. Record Launch Completed event
        evt_id = self.event_bus.publish(
            "PlatformLaunchCompleted",
            {
                "client": client,
                "project": project_id,
                "duration_seconds": round(duration, 3),
                "dashboard_api_online": dashboard_up,
                "gemini_router_online": router_up,
            },
            project=project_id,
            correlation_id=context.trace_id,
        )

        return {
            "status": "success",
            "client": client,
            "project": project_id,
            "duration_seconds": round(duration, 3),
            "services": {
                "dashboard_api_20129": dashboard_up,
                "gemini_router_20130": router_up,
                "sqlite_vec_db": True,
            },
            "session": session_info,
            "event_id": evt_id,
            "trace_id": context.trace_id,
        }


if __name__ == "__main__":
    raise SystemExit("Use python -m devcore_engine.cli launch --project <project>.")
