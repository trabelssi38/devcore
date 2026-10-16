"""Inspect two DevCore SQLite sources before a fusion.

The command is deliberately read-only for both source databases.  It writes
only a JSON report to the requested output path and never performs a merge.
The report is the input evidence for the later project/task/graph fusion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TABLES = (
    "projects",
    "tasks",
    "runs",
    "events",
    "bus_events",
    "audit_log",
    "kg_nodes",
    "kg_edges",
    "kg_edges_quarantine",
    "memory_entries",
    "run_history",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }


def _count(connection: sqlite3.Connection, table: str, tables: set[str]) -> int | None:
    if table not in tables:
        return None
    return int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def _schema(connection: sqlite3.Connection) -> tuple[dict[str, list[str]], dict[str, str]]:
    tables = _table_names(connection)
    columns: dict[str, list[str]] = {}
    errors: dict[str, str] = {}
    for table in sorted(tables):
        try:
            columns[table] = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
        except sqlite3.DatabaseError as exc:
            errors[table] = str(exc)
    return columns, errors


def _foreign_key_errors(connection: sqlite3.Connection) -> dict[str, Any]:
    try:
        cursor = connection.execute("PRAGMA foreign_key_check")
        total = 0
        by_table: dict[str, int] = {}
        examples: list[list[Any]] = []
        for row in cursor:
            total += 1
            table = str(row[0])
            by_table[table] = by_table.get(table, 0) + 1
            if len(examples) < 10:
                examples.append(list(row))
        return {"total": total, "by_table": by_table, "examples": examples, "error": None}
    except sqlite3.DatabaseError as exc:
        return {"total": None, "by_table": {}, "examples": [], "error": f"{type(exc).__name__}: {exc}"}


def inspect_source(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    wal_path = path.with_name(path.name + "-wal")
    if wal_path.exists() and wal_path.stat().st_size:
        raise ValueError(f"Non-empty WAL requires a coherent SQLite backup first: {path}")
    uri = f"file:{path.resolve().as_posix()}?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as connection:
        try:
            import sqlite_vec

            connection.enable_load_extension(True)
            try:
                sqlite_vec.load(connection)
            finally:
                connection.enable_load_extension(False)
        except ImportError:
            pass
        tables = _table_names(connection)
        schema, schema_errors = _schema(connection)
        return {
            "path": str(path.resolve()),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "tables": sorted(tables),
            "counts": {table: _count(connection, table, tables) for table in TABLES},
            "schema": schema,
            "schema_errors": schema_errors,
            "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_key_check": _foreign_key_errors(connection),
        }


def compare_sources(current: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
    current_tables = set(current["tables"])
    other_tables = set(other["tables"])
    count_deltas: dict[str, int | None] = {}
    for table in TABLES:
        left, right = current["counts"].get(table), other["counts"].get(table)
        count_deltas[table] = None if left is None or right is None else left - right
    return {
        "tables_only_current": sorted(current_tables - other_tables),
        "tables_only_other": sorted(other_tables - current_tables),
        "count_delta_current_minus_other": count_deltas,
        "schema_differences": {
            table: {
                "current_only": sorted(set(current["schema"].get(table, ())) - set(other["schema"].get(table, ()))),
                "other_only": sorted(set(other["schema"].get(table, ())) - set(current["schema"].get(table, ()))),
            }
            for table in sorted(current_tables | other_tables)
            if current["schema"].get(table, []) != other["schema"].get(table, [])
        },
    }


def compare_tasks(current_db: Path, other_db: Path) -> dict[str, Any]:
    """Classify matching task keys without deciding which version wins."""
    def read(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
        uri = f"file:{path.resolve().as_posix()}?mode=ro&immutable=1"
        with sqlite3.connect(uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("SELECT * FROM tasks")
            tasks: dict[tuple[str, str], dict[str, Any]] = {}
            for row in rows:
                payload = dict(row)
                key = (str(payload["project_id"]), str(payload["id"]))
                if key in tasks:
                    raise ValueError(f"Duplicate task key in {path}: {key}")
                tasks[key] = payload
            return tasks

    current = read(current_db)
    other = read(other_db)
    shared = current.keys() & other.keys()
    fields = sorted(set(next(iter(current.values()), {})) | set(next(iter(other.values()), {})))
    differences: Counter[str] = Counter()
    review_items: list[dict[str, Any]] = []
    for key in sorted(shared):
        changed = [field for field in fields if current[key].get(field) != other[key].get(field)]
        differences.update(changed)
        if changed:
            review_items.append({"project_id": key[0], "task_id": key[1], "fields": changed})
    return {
        "current_count": len(current),
        "other_count": len(other),
        "shared_keys": len(shared),
        "only_current": len(current.keys() - other.keys()),
        "only_other": len(other.keys() - current.keys()),
        "field_differences": dict(sorted(differences.items())),
        "review_items": review_items,
    }


def build_report(current_db: Path, other_db: Path, other_scheduler_db: Path | None = None) -> dict[str, Any]:
    current = inspect_source(current_db)
    other = inspect_source(other_db)
    report = {
        "report_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "sources": {"current": current, "other": other},
        "comparison": compare_sources(current, other),
        "task_comparison": compare_tasks(current_db, other_db),
        "merge_status": "inventory_only",
        "blocking_findings": {
            "current_foreign_key_errors": current["foreign_key_check"],
            "other_foreign_key_errors": other["foreign_key_check"],
        },
    }
    if other_scheduler_db is not None:
        report["other_scheduler"] = inspect_source(other_scheduler_db)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-db", type=Path, required=True)
    parser.add_argument("--other-db", type=Path, required=True)
    parser.add_argument("--other-scheduler-db", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.current_db, args.other_db, args.other_scheduler_db)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "read_only": True, "merge_status": "inventory_only"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
