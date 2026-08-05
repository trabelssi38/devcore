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
from devcore_engine.migrate_to_unified_db import DevCoreMigrator
from devcore_engine.services.events import EventBus
from devcore_engine.lifecycle.session import SessionManager


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

    def launch(self, client: str = "auto", project_id: str = "devcore") -> Dict[str, Any]:
        start_time = time.time()
        
        # 1. Idempotent Migration & DB Sync
        migrator = DevCoreMigrator()
        migration_stats = migrator.run_all()

        # 2. Check Native Services & Auto-Start if offline (detached background process)
        DETACHED_FLAG = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        dashboard_up = check_port("127.0.0.1", 20129)
        if not dashboard_up:
            try:
                subprocess.Popen(
                    [sys.executable, str(Path(__file__).parent.parent.parent / "Scripts" / "dashboard_api.py")],
                    cwd=str(Path(__file__).parent.parent.parent),
                    creationflags=DETACHED_FLAG,
                )
                for _ in range(10):
                    time.sleep(0.3)
                    if check_port("127.0.0.1", 20129):
                        dashboard_up = True
                        break
            except Exception:
                pass

        router_up = check_port("127.0.0.1", 20130)
        if not router_up:
            try:
                subprocess.Popen(
                    [sys.executable, str(Path(__file__).parent.parent.parent / "Scripts" / "gemini_router.py")],
                    cwd=str(Path(__file__).parent.parent.parent),
                    creationflags=DETACHED_FLAG,
                )
                for _ in range(10):
                    time.sleep(0.3)
                    if check_port("127.0.0.1", 20130):
                        router_up = True
                        break
            except Exception:
                pass



        # 3. Initialize Session Context
        session_info = self.session_manager.start_session(project_id)

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
        }


if __name__ == "__main__":
    launcher = PlatformLauncher()
    res = launcher.launch()
    print(f"[PlatformLauncher] Launch result: {res}")
