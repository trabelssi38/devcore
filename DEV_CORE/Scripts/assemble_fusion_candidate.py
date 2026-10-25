"""Assemble the reviewed fusion artifacts into a new SQLite candidate.

The current source is copied as the base. Mapping, graph-preview and scheduler
tables are copied into namespaced tables. No application table is replaced and
the output remains review-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    wal = path.with_name(path.name + "-wal")
    if wal.exists() and wal.stat().st_size:
        raise ValueError(f"Non-empty WAL requires a coherent SQLite backup: {path}")
    return sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True)


def _copy_table(source: sqlite3.Connection, target: sqlite3.Connection, source_table: str, target_table: str) -> int:
    columns = [(row[1], row[2] or "TEXT") for row in source.execute(f'PRAGMA table_info("{source_table}")')]
    if not columns:
        raise ValueError(f"Missing table: {source_table}")
    quoted = ", ".join('"' + name.replace('"', '""') + '"' for name, _kind in columns)
    target_columns = ", ".join('"' + name.replace('"', '""') + '" ' + kind for name, kind in columns)
    target.execute(f'CREATE TABLE "{target_table}" ({target_columns})')
    placeholders = ", ".join("?" for _ in columns)
    cursor = source.execute(f'SELECT {quoted} FROM "{source_table}"')
    count = 0
    while rows := cursor.fetchmany(10_000):
        target.executemany(f'INSERT INTO "{target_table}" ({quoted}) VALUES ({placeholders})', rows)
        count += len(rows)
    return count


def assemble(base_db: Path, mapping_db: Path, graph_preview_db: Path, scheduler_db: Path, output_db: Path, task_project_db: Path | None = None, graph_fk_db: Path | None = None) -> dict:
    if output_db.exists():
        raise FileExistsError(output_db)
    optional_paths = (("task_project", task_project_db), ("graph_fk", graph_fk_db))
    optional_paths = tuple((name, path) for name, path in optional_paths if path)
    source_paths = (base_db, mapping_db, graph_preview_db, scheduler_db) + tuple(path for _name, path in optional_paths)
    source_names = ("base", "mapping", "graph", "scheduler") + tuple(name for name, _path in optional_paths)
    source_hashes = {name: _sha256(path) for name, path in zip(source_names, source_paths)}
    output_db.parent.mkdir(parents=True, exist_ok=True)
    with _readonly(base_db) as base:
        with sqlite3.connect(output_db) as target:
            base.backup(target)
            target.executescript("""
                CREATE TABLE fusion_candidate_manifest (
                    created_utc TEXT NOT NULL, status TEXT NOT NULL,
                    base_source TEXT NOT NULL, mapping_source TEXT NOT NULL,
                    graph_source TEXT NOT NULL, scheduler_source TEXT NOT NULL,
                    source_sha256_json TEXT NOT NULL,
                    writes_to_application_tables INTEGER NOT NULL CHECK(writes_to_application_tables=0)
                );
            """)
            target.execute("INSERT INTO fusion_candidate_manifest VALUES (?, 'review_only', ?, ?, ?, ?, ?, 0)", (
                datetime.now(timezone.utc).isoformat(), str(base_db.resolve()), str(mapping_db.resolve()),
                str(graph_preview_db.resolve()), str(scheduler_db.resolve()), json.dumps(source_hashes, sort_keys=True)
            ))
            counts = {}
            with _readonly(mapping_db) as mapping:
                for source_table, target_table in (
                    ("project_merge_map", "fusion_project_merge_map"),
                    ("task_merge_map", "fusion_task_merge_map"),
                    ("task_field_conflicts", "fusion_task_field_conflicts"),
                ):
                    counts[target_table] = _copy_table(mapping, target, source_table, target_table)
            with _readonly(graph_preview_db) as graph:
                counts["fusion_kg_edges_repair_preview"] = _copy_table(graph, target, "kg_edges_repair_preview", "fusion_kg_edges_repair_preview")
            with _readonly(scheduler_db) as scheduler:
                counts["fusion_run_history_archive"] = _copy_table(scheduler, target, "run_history_archive", "fusion_run_history_archive")
            if task_project_db:
                with _readonly(task_project_db) as task_project:
                    counts["fusion_projects_fk_preview"] = _copy_table(task_project, target, "projects_fk_preview", "fusion_projects_fk_preview")
                    counts["fusion_tasks_fk_preview"] = _copy_table(task_project, target, "tasks_fk_preview", "fusion_tasks_fk_preview")
            if graph_fk_db:
                with _readonly(graph_fk_db) as graph_fk:
                    counts["fusion_graph_nodes_fk_preview"] = _copy_table(graph_fk, target, "kg_nodes_preview", "fusion_graph_nodes_fk_preview")
                    counts["fusion_graph_edges_fk_preview"] = _copy_table(graph_fk, target, "kg_edges_fk_preview", "fusion_graph_edges_fk_preview")
                    counts["fusion_graph_quarantine_preview"] = _copy_table(graph_fk, target, "kg_edges_quarantine_preview", "fusion_graph_quarantine_preview")
            integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
            target.commit()
    return {"output": str(output_db), "status": "review_only", "integrity": integrity, "attached_counts": counts,
            "writes_to_application_tables": False, "source_sha256": source_hashes,
            "created_utc": datetime.now(timezone.utc).isoformat()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-db", type=Path, required=True)
    parser.add_argument("--mapping-db", type=Path, required=True)
    parser.add_argument("--graph-preview-db", type=Path, required=True)
    parser.add_argument("--scheduler-db", type=Path, required=True)
    parser.add_argument("--output-db", type=Path, required=True)
    parser.add_argument("--task-project-db", type=Path)
    parser.add_argument("--graph-fk-db", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = assemble(args.base_db, args.mapping_db, args.graph_preview_db, args.scheduler_db, args.output_db, args.task_project_db, args.graph_fk_db)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
