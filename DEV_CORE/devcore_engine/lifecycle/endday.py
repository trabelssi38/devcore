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

from devcore_engine.db import connect_db, init_db
from devcore_engine.services.events import EventBus
from devcore_engine.services.memory import MemoryService
from devcore_engine.services.tasks import TaskService


class EndDayManager:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or init_db()
        self.event_bus = EventBus(self.conn)
        self.memory_service = MemoryService(self.conn)
        self.task_service = TaskService(self.conn)

    def run_endday(self, project_id: str = "devcore") -> Dict[str, Any]:
        today_str = datetime.date.today().isoformat()
        
        # 1. Rotate MEMORY file if threshold exceeded
        rotate_res = self.memory_service.rotate("MEMORY", threshold=300, keep_lines=200)

        # 2. Get completed tasks summary
        board = self.task_service.get_board(project_id)
        done_tasks = [t for t in board["tasks"] if t["status"] == "done"]

        # 3. Insert or update vault daily note record
        daily_path = f"Daily Notes/{today_str}.md"
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

        # 4. Record EndDayCompleted event
        evt_id = self.event_bus.publish(
            "EndDayCompleted",
            {
                "date": today_str,
                "project": project_id,
                "done_count": len(done_tasks),
                "memory_rotated": rotate_res["rotated"],
            },
            project=project_id,
        )

        self.conn.commit()

        return {
            "status": "success",
            "date": today_str,
            "project": project_id,
            "done_tasks_count": len(done_tasks),
            "memory_rotation": rotate_res,
            "event_id": evt_id,
        }


if __name__ == "__main__":
    edm = EndDayManager()
    res = edm.run_endday("devcore")
    print(f"[EndDayManager] Maintenance complete: {res}")
