"""
post_commit.py -- DEV_CORE Git Post-Commit Hook (Python Native)
Replaces shell logic in post-commit.hook by processing commits and mutating tasks in devcore.db.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import os
import re
import subprocess
import sqlite3
from typing import Optional

from devcore_engine.db import connect_db, init_db
from devcore_engine.services.events import EventBus
from devcore_engine.services.tasks import TaskService
from devcore_engine.lifecycle.session import SessionManager


def get_last_commit_message() -> str:
    try:
        res = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            capture_output=True,
            text=True,
            encoding="utf-8-sig",
            errors="replace",
        )
        return res.stdout.strip()
    except Exception:
        return ""


def run_post_commit_hook() -> None:
    msg = get_last_commit_message()
    if not msg or len(msg) < 4 or msg.startswith("Merge "):
        return

    conn = init_db()
    event_bus = EventBus(conn)
    task_service = TaskService(conn)
    session_mgr = SessionManager(conn)

    # Determine project_id from current git repository directory or fallback to active project
    git_repo_name = None
    try:
        git_res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8-sig",
            errors="replace"
        )
        if git_res.returncode == 0 and git_res.stdout.strip():
            git_repo_name = Path(git_res.stdout.strip()).name
    except Exception:
        pass

    project_id = git_repo_name or session_mgr.get_active_project()

    # Extract tag [T-XX]
    match = re.search(r"\[(T-\d+)\]", msg, re.IGNORECASE)
    tag_id = match.group(1).upper() if match else None

    if tag_id:
        print(f"  [DEV_CORE] Tag {tag_id} detecte dans le commit")
        task = task_service.get_task(tag_id)
        if task:
            # Rename generic task if needed
            clean_msg = re.sub(r"\[T-\d+\]", "", msg, flags=re.IGNORECASE).strip()
            if ("session de travail auto" in task["title"].lower() or task["title"].lower() in ["false", ""]) and clean_msg:
                task_service.edit_task(tag_id, title=clean_msg, project_id=project_id)
                print(f"  [DEV_CORE] Tache {tag_id} renommee en : {clean_msg}")

            # Increment step
            updated = task_service.step_task(tag_id, project_id=project_id)
            if updated:
                print(f"  [DEV_CORE] Step {updated['steps_done']}/{updated['steps_total']} enregistree pour '{tag_id}'")
                if updated["status"] == "done":
                    print(f"  [DEV_CORE] Tache '{tag_id}' marquee done")

            event_bus.publish(
                "GitCommitTagged",
                {"task_id": tag_id, "commit_msg": msg},
                project=project_id,
                task_id=tag_id,
            )
    else:
        # No tag: Adopt active generic session task or complete active task or auto-create new task
        print("  [DEV_CORE] Aucun tag detecte. Traitement autonome du commit...")
        active = task_service.next_task(project_id)
        clean_msg = msg.splitlines()[0].strip()
        if active:
            target_id = active["id"]
            if "session de travail auto" in active["title"].lower() or active["title"].lower().startswith("session") or active["title"].lower() in ["false", ""]:
                task_service.edit_task(target_id, title=clean_msg, project_id=project_id)
                print(f"  [DEV_CORE] Tache active {target_id} renommee en : {clean_msg}")
            
            task_service.complete_task(target_id, project_id=project_id)
            print(f"  [DEV_CORE] Tache active {target_id} marquee done")
        else:
            new_task = task_service.add_task(clean_msg, mode="coding", steps=1, project_id=project_id)
            target_id = new_task["id"]
            task_service.complete_task(target_id, project_id=project_id)
            print(f"  [DEV_CORE] Nouvelle tache {target_id} creee et marquee done pour le commit : {clean_msg}")

        event_bus.publish(
            "GitCommitAutoAdopted",
            {"task_id": target_id, "commit_msg": msg},
            project=project_id,
            task_id=target_id,
        )



if __name__ == "__main__":
    run_post_commit_hook()
