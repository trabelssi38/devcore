"""
endday.py -- DEV_CORE End-of-Day Maintenance Lifecycle (Python Native)
Replaces endday.ps1 by executing memory compaction, task metrics summary, and event archiving.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import datetime
import sqlite3
from typing import Any, Dict, Optional

from devcore_engine.context import RequestContext
from devcore_engine.db import connect_db, init_db
from devcore_engine.services.events import EventBus
from devcore_engine.services.tasks import TaskService, _validate_project_id


class EndDayManager:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or init_db()
        self.event_bus = EventBus(self.conn)
        self.task_service = TaskService(self.conn)

    def run_endday(self, project_id: str | RequestContext) -> Dict[str, Any]:
        context = project_id if isinstance(project_id, RequestContext) else RequestContext(project_id=_validate_project_id(project_id))
        project_id = context.project_id
        today_str = datetime.date.today().isoformat()

        # Shared memory has no project owner and cannot be rotated here.
        board = self.task_service.get_board(project_id)
        done_tasks = [t for t in board["tasks"] if t["status"] == "done"]

        # Keep the SQL note distinct from historical global daily notes.
        daily_path = f"Projects/{project_id}/Daily Notes/{today_str}.md"
        cursor = self.conn.cursor()
        existing_note = cursor.execute("SELECT content FROM vault_notes WHERE path = ?;", (daily_path,)).fetchone()
        
        note_content = existing_note["content"] if existing_note else f"# Daily Note {today_str}\n\n## Taches accomplies\n"
        
        acc_lines = ["\n## Taches accomplies"]
        for t in done_tasks[-10:]:
            acc_lines.append(f"- [x] **{t['id']}**: {t['title']}")

        if "## Taches accomplies" in note_content:
            # Append new completed tasks cleanly
            note_content = note_content.split("## Taches accomplies")[0] + "\n".join(acc_lines)
        else:
            note_content += "\n" + "\n".join(acc_lines)

        self.conn.execute(
            """
            INSERT INTO vault_notes (path, title, tags, content, updated_at)
            VALUES (?, ?, '["daily", "devcore"]', ?, datetime('now'))
            ON CONFLICT(path) DO UPDATE SET
                content = excluded.content,
                updated_at = datetime('now');
            """,
            (daily_path, f"Daily Note {today_str}", note_content),
        )

        # Record EndDayCompleted event in the same project.
        evt_id = self.event_bus.publish(
            "EndDayCompleted",
            {
                "date": today_str,
                "project": project_id,
                "done_count": len(done_tasks),
                "memory_rotated": False,
            },
            project=project_id,
            correlation_id=context.trace_id,
        )

        self.conn.commit()

        return {
            "status": "success",
            "date": today_str,
            "project": project_id,
            "done_tasks_count": len(done_tasks),
            "memory_rotation": None,
            "event_id": evt_id,
            "trace_id": context.trace_id,
        }


if __name__ == "__main__":
    edm = EndDayManager()
    res = edm.run_endday("devcore")
    print(f"[EndDayManager] Maintenance complete: {res}")
