"""
events.py -- DEV_CORE Event Bus Service (Python Native)
Replaces event_bus.ps1 by publishing and querying events directly in devcore.db.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import json
import sqlite3
import uuid
from typing import Any, Dict, List, Optional

from devcore_engine.db import connect_db, init_db


class EventBus:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or init_db()

    def publish(
        self,
        event_type: str,
        payload: Dict[str, Any] | str,
        source: str = "devcore",
        project: str = "devcore",
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        evt_id = f"evt_{uuid.uuid4().hex[:12]}"
        payload_json = json.dumps(payload) if isinstance(payload, dict) else str(payload)

        self.conn.execute(
            """
            INSERT INTO bus_events (id, source, event_type, project, task_id, correlation_id, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (evt_id, source, event_type, project, task_id, correlation_id, payload_json),
        )
        self.conn.commit()
        return evt_id

    def read(
        self,
        event_type: Optional[str] = None,
        project: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        query = "SELECT * FROM bus_events WHERE 1=1"
        params: List[Any] = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if project:
            query += " AND project = ?"
            params.append(project)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = cursor.execute(query, params).fetchall()
        results = []
        for r in rows:
            evt = dict(r)
            try:
                evt["payload"] = json.loads(evt["payload"])
            except Exception:
                pass
            results.append(evt)
        return results

    def tail(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.read(limit=limit)


if __name__ == "__main__":
    bus = EventBus()
    evt_id = bus.publish("test_event", {"status": "ok", "message": "Unified SQLite Event Bus operational"})
    print(f"[EventBus] Published test event: {evt_id}")
    recent = bus.tail(5)
    print(f"[EventBus] Retrieved {len(recent)} recent events:")
    for e in recent:
        print(f"  - [{e['created_at']}] {e['event_type']} from {e['source']}: {e['payload']}")
