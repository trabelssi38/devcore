"""Build a reviewable individual-pilot database from a reconciled SQLite copy.

The input is opened read-only. Legacy graph and vault rows without a project
are assigned to an archive project with no pilot user grants. Original task IDs
and all reconciled/quarantined graph rows remain in the destination.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sqlite3

from devcore_engine.db import connect_db


ARCHIVE_PROJECT = "__legacy_unassigned__"
PRESERVED_TABLES = (
    "projects", "tasks", "kg_nodes", "kg_edges", "kg_edges_quarantine",
    "vault_notes", "legacy_task_identity_map", "legacy_task_reference_report",
    "runtime_state", "bus_events", "memory_entries",
)


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')]


def _digest_rows(conn: sqlite3.Connection, table: str, columns: list[str],
                 *, exclude_archive: bool = False) -> tuple[int, str]:
    names = ", ".join(f'"{name}"' for name in columns)
    where = " WHERE id <> ?" if exclude_archive else ""
    args = (ARCHIVE_PROJECT,) if exclude_archive else ()
    digest = hashlib.sha256()
    count = 0
    for row in conn.execute(f'SELECT {names} FROM "{table}"{where} ORDER BY rowid', args):
        digest.update(json.dumps(tuple(row), ensure_ascii=False, default=str).encode("utf-8"))
        digest.update(b"\n")
        count += 1
    return count, digest.hexdigest()


def _task_number_plan(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        "SELECT project_id, legacy_task_id, task_number, number_status "
        "FROM legacy_task_identity_map ORDER BY project_id, legacy_task_id"
    ).fetchall()
    by_project: dict[str, list[tuple[str, int | None, str]]] = defaultdict(list)
    for project, task_id, number, status in rows:
        by_project[project].append((task_id, number, status))
    counters: Counter = Counter()
    for project, tasks in by_project.items():
        numeric: dict[int, list[str]] = defaultdict(list)
        for task_id, number, _ in tasks:
            if number is not None:
                if type(number) is not int:
                    raise ValueError("Invalid legacy task number")
                if number > 0:
                    numeric[number].append(task_id)
        chosen = {min(ids, key=lambda value: (len(value), value)): number
                  for number, ids in numeric.items()}
        next_number = max(numeric, default=0) + 1
        assignments = []
        for task_id, original_number, original_status in tasks:
            if task_id in chosen:
                proposed = chosen[task_id]
                status = "preserved"
            else:
                proposed = next_number
                next_number += 1
                if original_number is not None and original_number < 1:
                    status = "allocated_nonpositive"
                elif original_status == "unparseable":
                    status = "allocated_text"
                else:
                    status = "allocated_collision"
            counters[status] += 1
            assignments.append((proposed, status, project, task_id))
        conn.executemany(
            "UPDATE legacy_task_identity_map SET pilot_task_number=?, pilot_number_status=? "
            "WHERE project_id=? AND legacy_task_id=?", assignments
        )
    conn.execute(
        "CREATE UNIQUE INDEX idx_pilot_task_number_project "
        "ON legacy_task_identity_map(project_id, pilot_task_number)"
    )
    return dict(counters)


def prepare(source_path: Path, destination_path: Path) -> dict:
    source_path = Path(source_path).resolve(strict=True)
    destination_path = Path(destination_path).resolve()
    if source_path == destination_path or destination_path.exists():
        raise ValueError("Pilot destination must be new and distinct from source")
    source = sqlite3.connect(f"file:{source_path.as_posix()}?mode=ro", uri=True)
    destination = None
    try:
        if source.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise ValueError("Reconciled FK-preview version 1 required")
        if source.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Unresolved source foreign key violations")
        required = set(PRESERVED_TABLES) - {"runtime_state"}
        existing = {name for (name,) in source.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if not required <= existing or "legacy_runtime_state_report" not in existing:
            raise ValueError("Reconciliation tables are missing")
        if source.execute("SELECT 1 FROM projects WHERE id=?", (ARCHIVE_PROJECT,)).fetchone():
            raise ValueError("Archive project ID already exists")
        if source.execute("SELECT count(*) FROM tasks").fetchone()[0] != source.execute(
                "SELECT count(*) FROM legacy_task_identity_map").fetchone()[0]:
            raise ValueError("Incomplete legacy task identity mapping")
        columns = {table: _columns(source, table) for table in PRESERVED_TABLES if table in existing}
        before = {table: _digest_rows(source, table, names) for table, names in columns.items()}
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        with destination_path.open("xb"):
            pass
        destination = sqlite3.connect(destination_path)
        source.backup(destination)
        destination.execute("PRAGMA foreign_keys=OFF")
        destination.execute("BEGIN IMMEDIATE")
        destination.execute(
            "INSERT INTO projects(id,name,root_path,status,metadata) VALUES (?,?,?,?,?)",
            (ARCHIVE_PROJECT, "Legacy unassigned archive", "[unresolved]", "needs_review",
             json.dumps({"pilot_only": True, "user_grants": "none"})),
        )
        archived_tables = []
        for table in ("kg_nodes", "kg_edges", "kg_edges_quarantine", "vault_notes"):
            if "project_id" not in columns[table]:
                destination.execute(
                    f'ALTER TABLE "{table}" ADD COLUMN project_id TEXT NOT NULL '
                    f"DEFAULT '{ARCHIVE_PROJECT}'"
                )
                archived_tables.append(table)
        if "version" not in columns["tasks"]:
            destination.execute(
                "ALTER TABLE tasks ADD COLUMN version INTEGER NOT NULL DEFAULT 1 "
                "CHECK(version >= 1)"
            )
        destination.execute(
            "ALTER TABLE legacy_task_identity_map ADD COLUMN pilot_task_number INTEGER"
        )
        destination.execute(
            "ALTER TABLE legacy_task_identity_map ADD COLUMN pilot_number_status TEXT"
        )
        number_plan = _task_number_plan(destination)
        destination.commit()
        destination.close()
        destination = None

        # The installed engine creates current tables, indexes and triggers on
        # this disposable copy only. It must never be invoked on the source.
        pilot = connect_db(destination_path)
        try:
            after = {
                table: _digest_rows(pilot, table, names, exclude_archive=table == "projects")
                for table, names in columns.items()
            }
            if after != before:
                raise RuntimeError("Pilot copy changed preserved source rows")
            integrity = pilot.execute("PRAGMA integrity_check").fetchone()[0]
            violations = pilot.execute("PRAGMA foreign_key_check").fetchall()
            if integrity != "ok" or violations:
                raise RuntimeError("Pilot copy integrity or foreign keys failed")
            if not {"knowledge_items"} <= {
                    name for (name,) in pilot.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'")}:
                raise RuntimeError("Current engine schema is incomplete")
            if pilot.execute(
                "SELECT count(*) FROM legacy_task_identity_map WHERE pilot_task_number IS NULL "
                "OR pilot_task_number < 1"
            ).fetchone()[0]:
                raise RuntimeError("Pilot task number mapping incomplete")
            return {
                "source": str(source_path), "destination": str(destination_path),
                "integrity": integrity, "foreign_key_violations": 0,
                "preserved_counts": {table: count for table, (count, _) in before.items()},
                "number_plan": number_plan, "archived_legacy_tables": archived_tables,
                "archive_project": ARCHIVE_PROJECT,
                "pilot_copy_ready": True, "operationally_qualified": False,
            }
        finally:
            pilot.close()
    finally:
        source.close()
        if destination is not None:
            destination.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.destination), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
