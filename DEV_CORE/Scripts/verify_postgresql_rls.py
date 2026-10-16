"""Verify project isolation on the qualified PostgreSQL team schema."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import psycopg


def verify(host: str, port: int, database: str, admin_password: str, output: Path) -> dict:
    admin = psycopg.connect(host=host, port=port, user="postgres", password=admin_password, dbname=database)
    with admin.cursor() as cur:
        cur.execute("SELECT project_id, count(*) FROM tasks GROUP BY project_id ORDER BY count(*) DESC LIMIT 2")
        projects = [row[0] for row in cur.fetchall()]
        total = {pid: count for pid, count in cur.execute("SELECT project_id, count(*) FROM tasks GROUP BY project_id")}
    admin.close()
    if len(projects) < 2:
        raise RuntimeError("need two populated projects for RLS verification")
    app = psycopg.connect(host=host, port=port, user="devcore_app_qualification", password="DevCoreAppP3_2026_local", dbname=database)
    visible = []
    with app.cursor() as cur:
        for project in projects:
            cur.execute("SELECT set_config('app.current_project_id', %s, false)", (project,))
            cur.execute("SELECT count(*) FROM tasks")
            visible.append(cur.fetchone()[0])
    app.close()
    passed = visible == [total[projects[0]], total[projects[1]]] and visible[0] > 0 and visible[1] > 0
    result = {"report_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(), "status": "rls_verified" if passed else "rls_failed", "database": database, "projects": projects, "expected_counts": [total[p] for p in projects], "visible_counts": visible, "cross_project_isolation": passed, "blockers": [] if passed else ["rls_isolation_failed"]}
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"); return result


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--database",required=True); p.add_argument("--password",required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args(); result=verify("127.0.0.1",5432,a.database,a.password,a.output); print(json.dumps(result,ensure_ascii=False)); return 0 if result["status"] == "rls_verified" else 2


if __name__ == "__main__": raise SystemExit(main())
