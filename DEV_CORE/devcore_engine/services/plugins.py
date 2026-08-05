"""
plugins.py -- DEV_CORE Plugin SDK & Service (Python Native)
Replaces plugin_service.ps1 by executing plugin registration, validation, and status checks in devcore.db.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import json
import sqlite3
from typing import Any, Dict, List, Optional

from devcore_engine.db import connect_db, init_db
from devcore_engine.services.events import EventBus


class PluginService:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or init_db()
        self.event_bus = EventBus(self.conn)

    def list_plugins(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        rows = cursor.execute("SELECT * FROM plugins_registry ORDER BY name ASC;").fetchall()
        results = []
        for r in rows:
            p = dict(r)
            try:
                p["metadata"] = json.loads(p["metadata"])
            except Exception:
                pass
            results.append(p)
        return results

    def register_plugin(
        self,
        name: str,
        version: str = "1.0.0",
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        pid = name.lower()
        meta_json = json.dumps(metadata or {})
        self.conn.execute(
            """
            INSERT INTO plugins_registry (id, name, version, enabled, metadata)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                version = excluded.version,
                enabled = excluded.enabled,
                metadata = excluded.metadata;
            """,
            (pid, name, version, 1 if enabled else 0, meta_json),
        )
        self.conn.commit()
        self.event_bus.publish("PluginRegistered", {"plugin": name, "version": version, "enabled": enabled})

    def toggle_plugin(self, name: str, enabled: bool) -> bool:
        pid = name.lower()
        cursor = self.conn.cursor()
        res = cursor.execute(
            "UPDATE plugins_registry SET enabled = ? WHERE id = ?;",
            (1 if enabled else 0, pid),
        )
        self.conn.commit()
        updated = res.rowcount > 0
        if updated:
            self.event_bus.publish("PluginToggled", {"plugin": name, "enabled": enabled})
        return updated


if __name__ == "__main__":
    ps = PluginService()
    ps.register_plugin("memory_inspector", "1.0.0", True, {"author": "devcore"})
    plugins = ps.list_plugins()
    print(f"[PluginService] Total registered plugins: {len(plugins)}")
    for p in plugins:
        print(f"  - [{ 'ENABLED' if p['enabled'] else 'DISABLED' }] {p['name']} v{p['version']}")
