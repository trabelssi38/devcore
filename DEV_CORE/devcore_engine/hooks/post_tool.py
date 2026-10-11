"""
post_tool.py -- DEV_CORE Post-Tool Execution Hook (Python Native)
Replaces post_tool_hook.ps1 by logging metrics and tool execution events into devcore.db.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import json
from typing import Any, Dict, Optional

from devcore_engine.context import project_from_directory, validate_project_id
from devcore_engine.db import init_db
from devcore_engine.services.events import EventBus


def run_post_tool_hook(tool_name: str = "Bash", payload: Optional[Dict[str, Any]] = None,
                       project_id: Optional[str] = None) -> None:
    project_id = project_id or project_from_directory()
    if not project_id:
        return
    project_id = validate_project_id(project_id)

    conn = init_db()
    event_bus = EventBus(conn)

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
