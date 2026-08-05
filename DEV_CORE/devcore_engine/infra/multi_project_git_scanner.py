"""
multi_project_git_scanner.py -- DEV_CORE Multi-Project Git Commit Scanner
Scans git repositories of all registered projects in projects.json, ensuring all recent commits
are recorded as completed tasks in SQLite devcore.db and visible on the Cockpit dashboard.
"""

from __future__ import annotations
import sys
import os
import re
import json
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

DEV_CORE_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(DEV_CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(DEV_CORE_ROOT))

from devcore_engine.db import init_db, get_data_root


class MultiProjectGitScanner:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or init_db()
        self.data_root = get_data_root()
        self.projects_json = DEV_CORE_ROOT / "Config" / "projects.json"

    def load_projects(self) -> List[Dict[str, str]]:
        if not self.projects_json.exists():
            return []
        try:
            data = json.loads(self.projects_json.read_text(encoding="utf-8-sig"))
            return data.get("projects", [])
        except Exception as e:
            print(f"[GitScanner] Error reading projects.json: {e}", file=sys.stderr)
            return []

    def scan_project_repo(self, name: str, repo_path: Path, days: int = 30) -> int:
        if not repo_path.exists() or not repo_path.is_dir():
            return 0

        # Run git log
        try:
            res = subprocess.run(
                ["git", "log", f"--since={days} days ago", "--format=%H|%s|%ai"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                encoding="utf-8-sig",
                errors="replace"
            )
            if res.returncode != 0 or not res.stdout.strip():
                return 0

            lines = res.stdout.strip().splitlines()
        except Exception:
            return 0

        new_count = 0
        cur = self.conn.cursor()

        # Get existing task titles & commit hashes for this project
        cur.execute("SELECT id, title, metadata FROM tasks WHERE project_id=?", (name,))
        existing_rows = cur.fetchall()
        existing_ids = {r[0] for r in existing_rows}
        existing_titles = {r[1].strip().lower() for r in existing_rows if r[1]}

        for line in lines:
            if not line.strip() or "|" not in line:
                continue

            parts = line.split("|", 2)
            commit_hash = parts[0].strip()
            msg = parts[1].strip()
            date_str = parts[2].strip() if len(parts) > 2 else time.strftime("%Y-%m-%d %H:%M:%S")

            if not msg or len(msg) < 3 or msg.startswith("Merge "):
                continue

            # Check if tag [T-XX] is present in commit message
            match = re.search(r"\[(T-\d+)\]", msg, re.IGNORECASE)
            if match:
                task_id = match.group(1).upper()
                clean_title = re.sub(r"\[T-\d+\]", "", msg, flags=re.IGNORECASE).strip()
            else:
                # Deterministic ID for non-tagged commits: T-GIT-<short_hash>
                short_hash = commit_hash[:7]
                task_id = f"T-GIT-{short_hash.upper()}"
                clean_title = msg.splitlines()[0].strip()

            # Format details metadata
            details = f"**Actions détectées dans le commit Git ({short_hash if 'short_hash' in locals() else commit_hash[:7]}) :**\n- {clean_title}"

            if task_id in existing_ids:
                # Update existing task if missing metadata or status not done
                cur.execute("""
                    UPDATE tasks
                    SET status='done',
                        metadata=CASE WHEN (metadata IS NULL OR metadata='') THEN ? ELSE metadata END,
                        completed_at=CASE WHEN (completed_at IS NULL OR completed_at='') THEN ? ELSE completed_at END,
                        updated_at=datetime('now')
                    WHERE id=? AND project_id=?
                """, (details, date_str, task_id, name))
            elif clean_title.lower() not in existing_titles:
                # Insert new task for this commit
                cur.execute("""
                    INSERT INTO tasks (id, project_id, title, status, mode, steps_total, steps_done, metadata, started_at, completed_at, created_at, updated_at)
                    VALUES (?, ?, ?, 'done', 'git', 1, 1, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(id) DO UPDATE SET
                        project_id=excluded.project_id,
                        title=excluded.title,
                        status='done',
                        metadata=excluded.metadata,
                        completed_at=excluded.completed_at,
                        updated_at=datetime('now')
                """, (task_id, name, clean_title, details, date_str, date_str, date_str))
                existing_ids.add(task_id)
                existing_titles.add(clean_title.lower())
                new_count += 1

        self.conn.commit()
        return new_count

    def scan_all_projects(self, days: int = 30) -> Dict[str, int]:
        projects = self.load_projects()
        results = {}
        total_new = 0

        for p in projects:
            p_name = p.get("name")
            p_path = p.get("path")
            if not p_name or not p_path:
                continue

            repo_path = Path(p_path)
            added = self.scan_project_repo(p_name, repo_path, days=days)
            if added > 0:
                results[p_name] = added
                total_new += added

        # Also sync tasks.json for backward compatibility
        try:
            from devcore_engine.infra.system_watcher import SystemWatcher
            # Trigger gen_dashboard.py if commits were added
            if total_new > 0:
                gen_dash_script = DEV_CORE_ROOT / "Scripts" / "gen_dashboard.py"
                subprocess.run([sys.executable, str(gen_dash_script)], capture_output=True)
        except Exception:
            pass

        return {
            "total_new_tasks": total_new,
            "scanned_projects": results
        }


if __name__ == "__main__":
    scanner = MultiProjectGitScanner()
    res = scanner.scan_all_projects()
    print(f"[MultiProjectGitScanner] Scan completed: {res}")
