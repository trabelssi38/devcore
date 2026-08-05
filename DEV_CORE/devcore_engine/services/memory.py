"""
memory.py -- DEV_CORE Memory Service (Python Native)
Replaces memory_service.ps1 by storing and reading L0-L3 memory directly in devcore.db.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import sqlite3
from typing import Any, Dict, Optional

from devcore_engine.db import connect_db, init_db


class MemoryService:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or init_db()

    def get_text(self, name: str, task_type: str = "devcore") -> str:
        cursor = self.conn.cursor()
        row = cursor.execute(
            "SELECT content FROM memory_entries WHERE name = ? AND task_type = ?;",
            (name.upper(), task_type.lower()),
        ).fetchone()
        if row:
            return row["content"]
        
        # Fallback to default task_type if scenario not found
        if name.upper() == "SCENARIO" and task_type != "devcore":
            row = cursor.execute(
                "SELECT content FROM memory_entries WHERE name = 'SCENARIO' AND task_type = 'devcore';",
            ).fetchone()
            if row:
                return row["content"]
        return ""

    def write_text(self, name: str, content: str, task_type: str = "devcore") -> None:
        self.conn.execute(
            """
            INSERT INTO memory_entries (name, task_type, content, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(name, task_type) DO UPDATE SET
                content = excluded.content,
                version = version + 1,
                updated_at = datetime('now');
            """,
            (name.upper(), task_type.lower(), content),
        )
        self.conn.commit()

    def append_text(self, name: str, content: str, task_type: str = "devcore") -> str:
        current = self.get_text(name, task_type)
        updated = (current + "\n" + content).strip() if current else content.strip()
        self.write_text(name, updated, task_type)
        return updated

    def rotate(self, name: str = "MEMORY", threshold: int = 300, keep_lines: int = 200, task_type: str = "devcore") -> Dict[str, Any]:
        current = self.get_text(name, task_type)
        lines = current.splitlines()
        result = {
            "name": name,
            "total_lines": len(lines),
            "rotated": False,
            "retained_lines": len(lines),
        }

        if len(lines) > threshold:
            retained = lines[:keep_lines]
            new_content = "\n".join(retained)
            self.write_text(name, new_content, task_type)
            result["rotated"] = True
            result["retained_lines"] = len(retained)

        return result


if __name__ == "__main__":
    service = MemoryService()
    print("[MemoryService] Persona content sample:")
    print(service.get_text("PERSONA")[:200])
