"""Render one immutable PostgreSQL project-day snapshot supplied by the dispatcher."""

from __future__ import annotations

import argparse
from datetime import date
import json
import os


COUNTS = ("tasks_created", "tasks_completed", "runs_succeeded", "runs_failed")


def render(project: str, day: str, snapshot: dict) -> dict:
    if os.environ.get("DEVCORE_PROJECT_ID") != project:
        raise ValueError("Run project mismatch")
    date.fromisoformat(day)
    if not isinstance(snapshot, dict) or set(snapshot) != set(COUNTS):
        raise ValueError("Qualified metric snapshot required")
    if any(type(snapshot[key]) is not int or snapshot[key] < 0 for key in COUNTS):
        raise ValueError("Non-negative PostgreSQL counters required")
    return {"project": project, "day": day, "metrics": snapshot,
            "source": "project_postgres_snapshot", "task_changes": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--day", required=True)
    parser.add_argument("--snapshot-json", required=True)
    args = parser.parse_args(argv)
    try:
        if len(args.snapshot_json.encode("utf-8")) > 1024:
            raise ValueError("Metric snapshot exceeds bound")
        result = render(args.project, args.day, json.loads(args.snapshot_json))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (ValueError, TypeError):
        print(json.dumps({"status": "failed", "error": "invalid_snapshot"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
