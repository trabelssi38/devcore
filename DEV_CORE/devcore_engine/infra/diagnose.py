"""
diagnose.py -- DEV_CORE Diagnostic & Repair Engine (Python Native)
Replaces diagnose.ps1 by auditing system environment, database, APIs, and hooks.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import os
import socket
import sqlite3
from typing import Any, Dict, List

from devcore_engine.db import connect_db, get_data_root, get_db_path, HAS_SQLITE_VEC


def check_port(host: str, port: int, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


class DiagnosticEngine:
    def __init__(self, data_root: Optional[Path] = None):
        self.data_root = data_root or get_data_root()
        self.db_path = get_db_path()

    def run_diagnostics(self) -> Dict[str, Any]:
        checks = []

        # 1. DB File Check
        db_exists = self.db_path.exists()
        db_size_kb = round(self.db_path.stat().st_size / 1024, 1) if db_exists else 0
        checks.append({
            "name": "SQLite Database (devcore.db)",
            "status": "PASS" if db_exists else "FAIL",
            "details": f"Path: {self.db_path} ({db_size_kb} KB)",
        })

        # 2. sqlite-vec Extension Check
        checks.append({
            "name": "sqlite-vec Extension",
            "status": "PASS" if HAS_SQLITE_VEC else "FAIL",
            "details": "Installed and enabled" if HAS_SQLITE_VEC else "Not found in Python environment",
        })

        # 3. DB Connectivity & Tables Check
        tables_count = 0
        if db_exists:
            try:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                tables_count = cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';").fetchone()[0]
                conn.close()
                checks.append({
                    "name": "Database Tables",
                    "status": "PASS" if tables_count > 10 else "WARN",
                    "details": f"{tables_count} tables initialized",
                })
            except Exception as e:
                checks.append({
                    "name": "Database Tables",
                    "status": "FAIL",
                    "details": str(e),
                })

        # 4. Dashboard API check (Port 20129)
        dash_up = check_port("127.0.0.1", 20129)
        checks.append({
            "name": "Dashboard API (Port 20129)",
            "status": "PASS" if dash_up else "WARN",
            "details": "Online" if dash_up else "Offline",
        })

        # 5. Gemini Router check (Port 20130)
        router_up = check_port("127.0.0.1", 20130)
        checks.append({
            "name": "Gemini Router (Port 20130)",
            "status": "PASS" if router_up else "WARN",
            "details": "Online" if router_up else "Offline",
        })

        # 6. Headroom Proxy check (Port 8787)
        headroom_up = check_port("127.0.0.1", 8787)
        checks.append({
            "name": "Headroom Proxy (Port 8787)",
            "status": "PASS" if headroom_up else "WARN",
            "details": "Online" if headroom_up else "Offline",
        })

        all_pass = all(c["status"] == "PASS" for c in checks)
        return {
            "overall_status": "PASS" if all_pass else "WARN",
            "checks": checks,
        }


if __name__ == "__main__":
    diag = DiagnosticEngine()
    report = diag.run_diagnostics()
    print(f"=== DEV_CORE DIAGNOSTIC REPORT ({report['overall_status']}) ===")
    for c in report["checks"]:
        print(f"  [{c['status']:4s}] {c['name']} -- {c['details']}")
