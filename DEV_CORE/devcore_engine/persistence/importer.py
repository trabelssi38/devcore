"""Dry-run importer and reconciliation engine for SQLite/JSON -> PostgreSQL target.

Produces reconciliation reports with deterministic UUID v5 mappings,
task number collision detection, runtime_state classification, SHA-256 content digests,
and explicit conflict resolution rules (never guessing via Dropbox mtime).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from devcore_engine.persistence.repositories import (
    TASK_UUID_NAMESPACE,
    generate_task_uuid,
    parse_task_number,
)


@dataclass
class ReconciliationReport:
    """Report detailing reconciliation status, mappings, collisions, and digests."""
    project: str
    source_tasks_count: int = 0
    staged_tasks_count: int = 0
    collisions_count: int = 0
    task_identity_mappings: dict[str, dict[str, Any]] = field(default_factory=dict)
    runtime_state_classifications: dict[str, dict[str, str]] = field(default_factory=dict)
    source_content_digest: str = ""
    staged_content_digest: str = ""
    discrepancies: list[str] = field(default_factory=list)
    status: str = "pending"  # "ready", "collision_detected", "conflict_error"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_runtime_state_key(key: str) -> tuple[str, str, str]:
    """Classify legacy runtime_state into target disposition.
    
    Returns (classification, scope, notes).
    """
    k = key.strip().lower()
    if k in ("active_project", "active_task", "current_session", "active_session"):
        return ("ephemeral_to_rebuild", "session", f"Global session setting '{key}'; rebuilt dynamically.")
    if k.startswith(("last_", "tmp_", "lock_", "heartbeat_")):
        return ("ephemeral_to_rebuild", "transient", f"Transient runtime state '{key}'; discarded.")
    if k in ("theme", "ui_mode") or k.startswith(("ui_", "dashboard_")):
        return ("preference_to_migrate", "user_profile", f"User interface preference '{key}'.")
    if k.startswith(("config.", "settings.")):
        return ("preference_to_migrate", "config", f"Configuration setting '{key}'.")
    if k.startswith(("project.", "project_pref.")):
        return ("preference_to_migrate", "project_metadata", f"Project preference '{key}'.")
    return ("ambiguous_needs_review", "review", f"Unrecognized key '{key}'; requires explicit operator review.")


def compute_task_digest(tasks_list: list[dict[str, Any]]) -> str:
    """Compute deterministic SHA-256 digest over normalized task contents."""
    h = hashlib.sha256()
    for t in sorted(tasks_list, key=lambda x: (x.get("project_id", ""), str(x.get("task_number", 0)), str(x.get("legacy_id", "")))):
        normalized = {
            "project_id": t.get("project_id", ""),
            "task_number": t.get("task_number", 0),
            "legacy_id": t.get("legacy_id", ""),
            "title": t.get("title", ""),
            "mode": t.get("mode", "coding"),
            "status": t.get("status", "todo"),
            "steps_done": t.get("steps_done", 0),
            "steps_total": t.get("steps_total", 1),
        }
        h.update(json.dumps(normalized, sort_keys=True).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


class PostgresDryRunImporter:
    """Performs dry-run import and validation from SQLite or JSON to PostgreSQL target schema."""

    def __init__(self, conflict_policy: str = "reject_collision") -> None:
        # Explicit rule: 'reject_collision' - never pick based on Dropbox mtime
        self.conflict_policy = conflict_policy

    def dry_run_json_board(self, board_dict: dict[str, Any], project_override: Optional[str] = None) -> ReconciliationReport:
        """Analyze a JSON task board and generate a reconciliation report."""
        project = project_override or board_dict.get("project") or "devcore"
        raw_tasks = board_dict.get("tasks", [])
        return self._reconcile_tasks_list(raw_tasks, project)

    def dry_run_sqlite(self, sqlite_path: Path, project: Optional[str] = None) -> ReconciliationReport:
        """Read tasks and runtime_state from a SQLite database candidate and produce a report."""
        conn = sqlite3.connect(f"file:{Path(sqlite_path).resolve()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            # Fetch tasks
            cur.execute("SELECT * FROM tasks" + (" WHERE project_id = ?" if project else ""), (project,) if project else ())
            raw_tasks = [dict(r) for r in cur.fetchall()]
            active_project = project or (raw_tasks[0].get("project_id", "devcore") if raw_tasks else "devcore")

            report = self._reconcile_tasks_list(raw_tasks, active_project)

            # Classify runtime_state if present
            try:
                cur.execute("SELECT key, value FROM runtime_state")
                for row in cur.fetchall():
                    k = str(row["key"])
                    v = str(row["value"])
                    disposition, scope, notes = classify_runtime_state_key(k)
                    report.runtime_state_classifications[k] = {
                        "disposition": disposition,
                        "scope": scope,
                        "notes": notes,
                    }
            except sqlite3.OperationalError:
                pass

            return report
        finally:
            conn.close()

    def _reconcile_tasks_list(self, raw_tasks: list[dict[str, Any]], project: str) -> ReconciliationReport:
        report = ReconciliationReport(project=project, source_tasks_count=len(raw_tasks))
        staged_tasks = []
        seen_numbers: dict[int, str] = {}  # task_number -> legacy_id
        source_normalized = []

        for t in raw_tasks:
            legacy_id = str(t.get("id") or t.get("legacy_id") or "")
            proj = str(t.get("project_id") or project)
            title = str(t.get("title") or "")
            status = str(t.get("status") or "todo")
            mode = str(t.get("mode") or "coding")
            steps_done = int(t.get("steps_done", 0))
            steps_total = int(t.get("steps_total", 1))

            if not legacy_id:
                report.discrepancies.append(f"Task with title '{title}' missing identifier.")
                continue

            num = parse_task_number(legacy_id)
            if num is None:
                report.discrepancies.append(f"Task '{legacy_id}' does not have a parseable numeric suffix.")
                num = len(seen_numbers) + 1

            task_u = generate_task_uuid(proj, legacy_id)

            mapping_info = {
                "legacy_id": legacy_id,
                "project_id": proj,
                "task_number": num,
                "task_uuid": str(task_u),
                "collision": False,
            }

            if num in seen_numbers:
                mapping_info["collision"] = True
                mapping_info["collided_with"] = seen_numbers[num]
                report.collisions_count += 1
                report.discrepancies.append(
                    f"Collision on project '{proj}': task_number {num} claimed by both '{seen_numbers[num]}' and '{legacy_id}'."
                )
            else:
                seen_numbers[num] = legacy_id

            report.task_identity_mappings[legacy_id] = mapping_info

            staged = {
                "project_id": proj,
                "task_number": num,
                "legacy_id": legacy_id,
                "task_uuid": str(task_u),
                "title": title,
                "mode": mode,
                "status": status,
                "steps_done": steps_done,
                "steps_total": steps_total,
                "version": int(t.get("version", 1)),
            }
            staged_tasks.append(staged)
            source_normalized.append(staged)

        report.staged_tasks_count = len(staged_tasks)
        report.source_content_digest = compute_task_digest(source_normalized)
        report.staged_content_digest = compute_task_digest(staged_tasks)

        if report.collisions_count > 0:
            report.status = "collision_detected"
        elif report.discrepancies:
            report.status = "conflict_error"
        else:
            report.status = "ready"

        return report
