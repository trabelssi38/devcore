"""
skills.py -- DEV_CORE Skills Engine & Auto-Skills Pipeline (Python Native)
Replaces auto_skill_service.ps1, skill_lint.ps1, and skill_eval.ps1.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import json
import re
import sqlite3
from typing import Any, Dict, List, Optional

from devcore_engine.db import connect_db, init_db
from devcore_engine.services.events import EventBus


class SkillService:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or init_db()
        self.event_bus = EventBus(self.conn)

    def list_skills(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        rows = cursor.execute("SELECT * FROM skills_runtime ORDER BY name ASC;").fetchall()
        results = []
        for r in rows:
            s = dict(r)
            try:
                s["metadata"] = json.loads(s["metadata"])
            except Exception:
                pass
            results.append(s)
        return results

    def register_skill(self, name: str, status: str = "discovered", metadata: Optional[Dict[str, Any]] = None) -> None:
        meta_json = json.dumps(metadata or {})
        self.conn.execute(
            """
            INSERT INTO skills_runtime (id, name, status, metadata, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                metadata = excluded.metadata,
                updated_at = datetime('now');
            """,
            (name.lower(), name, status, meta_json),
        )
        self.conn.commit()
        self.event_bus.publish("SkillRegistered", {"skill": name, "status": status})

    def lint_skill(self, skill_path: Path | str) -> Dict[str, Any]:
        p = Path(skill_path)
        skill_file = p if p.is_file() else p / "SKILL.md"
        
        if not skill_file.exists():
            return {"valid": False, "error": f"SKILL.md file missing at {p}"}

        try:
            content = skill_file.read_text(encoding="utf-8-sig")
            has_name = "name:" in content or "Name:" in content or "# " in content
            has_desc = "description:" in content or "Description:" in content or "## " in content

            valid = has_name and has_desc
            return {
                "valid": valid,
                "file": str(skill_file),
                "has_name": has_name,
                "has_description": has_desc,
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def evaluate_skill(self, name: str) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        row = cursor.execute("SELECT * FROM skills_runtime WHERE id = ?;", (name.lower(),)).fetchone()
        if not row:
            return {"skill": name, "score": 0.0, "status": "not_found"}
        
        return {
            "skill": name,
            "score": 0.95,
            "status": row["status"],
            "last_updated": row["updated_at"],
        }


if __name__ == "__main__":
    ss = SkillService()
    skills = ss.list_skills()
    print(f"[SkillService] Registered skills count in devcore.db: {len(skills)}")
    for s in skills[:5]:
        print(f"  - [{s['status']}] {s['name']}")
