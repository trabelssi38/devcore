"""
post_tool.py -- DEV_CORE Post-Tool Execution Hook (Python Native)
Replaces post_tool_hook.ps1 by logging metrics and tool execution events into devcore.db.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import json
import os
import sqlite3
from typing import Any, Dict, Optional

from devcore_engine.db import connect_db, init_db
from devcore_engine.services.events import EventBus
from devcore_engine.lifecycle.session import SessionManager


def run_post_tool_hook(tool_name: str = "Bash", payload: Optional[Dict[str, Any]] = None) -> None:
    conn = init_db()
    event_bus = EventBus(conn)
    session_mgr = SessionManager(conn)

    project_id = session_mgr.get_active_project()

    # Record ToolExecuted event
    event_bus.publish(
        "ToolExecuted",
        {
            "tool": tool_name,
            "payload": payload or {},
        },
        project=project_id,
    )

    # Record metric
    conn.execute(
        """
        INSERT INTO metrics (source, project, metric_type, value, unit, payload)
        VALUES ('post_tool_hook', ?, 'tool_execution', 1.0, 'count', ?);
        """,
        (project_id, json.dumps({"tool": tool_name})),
    )
    conn.commit()


if __name__ == "__main__":
    run_post_tool_hook("Python", {"status": "ok"})
