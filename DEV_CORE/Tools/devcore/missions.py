# missions.py — DEV_CORE v6
# Mission board Python interface

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from devcore.paths import get_paths


def _missions_path() -> Path:
    return get_paths().memory_root / "missions.json"


def load_board() -> dict:
    p = _missions_path()
    if not p.exists():
        return {"project": "default", "current_mission": None,
                "active_client": "claude", "missions": []}
    return json.loads(p.read_text(encoding="utf-8"))


def save_board(board: dict) -> None:
    _missions_path().write_text(json.dumps(board, indent=2), encoding="utf-8")


def get_active_mission(board: dict) -> dict | None:
    return next((m for m in board["missions"] if m["status"] == "active"), None)


def get_next_todo(board: dict) -> dict | None:
    done_ids = {m["id"] for m in board["missions"] if m["status"] == "done"}
    for m in board["missions"]:
        if m["status"] != "todo":
            continue
        dep = m.get("depends_on")
        if dep is None or dep in done_ids:
            return m
    return None


def mark_active(board: dict, mission_id: str) -> None:
    for m in board["missions"]:
        if m["id"] == mission_id:
            m["status"] = "active"
            m["started_at"] = datetime.now(timezone.utc).isoformat()
            board["current_mission"] = mission_id
            return


def mark_done(board: dict, mission_id: str) -> None:
    for m in board["missions"]:
        if m["id"] == mission_id:
            m["status"] = "done"
            m["completed_at"] = datetime.now(timezone.utc).isoformat()
            return


def increment_step(board: dict, mission_id: str) -> dict | None:
    for m in board["missions"]:
        if m["id"] == mission_id:
            current = m.get("steps_done", 0)
            total = m.get("steps_total", 1)
            m["steps_done"] = min(current + 1, total)
            return m
    return None


def add_mission(board: dict, title: str, agent: str = "claude",
                depends_on: str | None = None) -> dict:
    existing_ids = [m["id"] for m in board["missions"]]
    nums = [int(mid.split("-")[1]) for mid in existing_ids
            if mid.startswith("M-") and mid.split("-")[1].isdigit()]
    next_num = (max(nums) + 1) if nums else 1
    mission = {
        "id": f"M-{next_num:02d}",
        "title": title,
        "agent": agent,
        "status": "todo",
        "steps_total": 1,
        "steps_done": 0,
        "depends_on": depends_on,
    }
    board["missions"].append(mission)
    return mission
