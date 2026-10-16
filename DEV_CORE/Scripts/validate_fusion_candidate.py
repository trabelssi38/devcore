"""Audit an assembled fusion review copy against its pinned source files."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


APPLICATION_TABLES = ("projects", "tasks", "kg_nodes", "kg_edges", "bus_events")
EXPECTED_AUXILIARY = {
    "fusion_project_merge_map": "project_merge_map",
    "fusion_task_merge_map": "task_merge_map",
    "fusion_task_field_conflicts": "task_field_conflicts",
    "fusion_kg_edges_repair_preview": "kg_edges_repair_preview",
    "fusion_run_history_archive": "run_history_archive",
}


def _open_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    wal = path.with_name(path.name + "-wal")
    if wal.exists() and wal.stat().st_size:
        raise ValueError(f"Non-empty WAL requires a coherent SQLite backup: {path}")
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True)
    try:
        import sqlite_vec

        connection.enable_load_extension(True)
        try:
            sqlite_vec.load(connection)
        finally:
            connection.enable_load_extension(False)
    except ImportError:
        pass
    return connection


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _table_digest(connection: sqlite3.Connection, table: str) -> tuple[int, str]:
    digest = hashlib.sha256()
    count = 0
    for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid'):
        digest.update(json.dumps(tuple(row), ensure_ascii=False, default=str).encode("utf-8"))
        digest.update(b"\n")
        count += 1
    return count, digest.hexdigest()


def _foreign_keys(connection: sqlite3.Connection) -> dict:
    counts: Counter[str] = Counter()
    try:
        for table, _rowid, _parent, _fkid in connection.execute("PRAGMA foreign_key_check"):
            counts[str(table)] += 1
        return {"total": sum(counts.values()), "by_table": dict(counts), "error": None}
    except sqlite3.DatabaseError as exc:
        return {"total": None, "by_table": {}, "error": f"{type(exc).__name__}: {exc}"}


def validate(base_db: Path, mapping_db: Path, graph_db: Path, scheduler_db: Path, candidate_db: Path, task_project_db: Path | None = None, graph_fk_db: Path | None = None) -> dict:
    sources = {"base": base_db, "mapping": mapping_db, "graph": graph_db, "scheduler": scheduler_db}
    if task_project_db:
        sources["task_project"] = task_project_db
    if graph_fk_db:
        sources["graph_fk"] = graph_fk_db
    with _open_readonly(base_db) as base, _open_readonly(mapping_db) as mapping, \
            _open_readonly(graph_db) as graph, _open_readonly(scheduler_db) as scheduler, \
            _open_readonly(candidate_db) as candidate:
        manifest = candidate.execute("SELECT status, source_sha256_json, writes_to_application_tables FROM fusion_candidate_manifest").fetchone()
        application = {}
        for table in APPLICATION_TABLES:
            before_count, before_digest = _table_digest(base, table)
            after_count, after_digest = _table_digest(candidate, table)
            application[table] = {
                "source_rows": before_count,
                "candidate_rows": after_count,
                "content_equal": before_digest == after_digest,
            }
        attached = {}
        expected_auxiliary = dict(EXPECTED_AUXILIARY)
        if task_project_db:
            expected_auxiliary.update({"fusion_projects_fk_preview": "projects_fk_preview", "fusion_tasks_fk_preview": "tasks_fk_preview"})
        if graph_fk_db:
            expected_auxiliary.update({"fusion_graph_nodes_fk_preview": "kg_nodes_preview", "fusion_graph_edges_fk_preview": "kg_edges_fk_preview", "fusion_graph_quarantine_preview": "kg_edges_quarantine_preview"})
        for target_table, source_table in expected_auxiliary.items():
            source_connection = mapping if target_table.startswith("fusion_project") or target_table.startswith("fusion_task") else graph if target_table.startswith("fusion_kg") else scheduler
            if target_table.startswith("fusion_projects_fk") or target_table.startswith("fusion_tasks_fk"):
                source_connection = _open_readonly(task_project_db)
            elif target_table.startswith("fusion_graph_"):
                source_connection = _open_readonly(graph_fk_db)
            source_count = source_connection.execute(f'SELECT COUNT(*) FROM "{source_table}"').fetchone()[0]
            target_count = candidate.execute(f'SELECT COUNT(*) FROM "{target_table}"').fetchone()[0]
            attached[target_table] = {"source_rows": source_count, "candidate_rows": target_count, "count_equal": source_count == target_count}
            if source_connection is not mapping and source_connection is not graph and source_connection is not scheduler and source_connection is not base:
                source_connection.close()
        preview_status = dict(candidate.execute(
            "SELECT status, COUNT(*) FROM fusion_kg_edges_repair_preview GROUP BY status"
        ).fetchall())
        project_review = candidate.execute(
            "SELECT COUNT(*) FROM fusion_project_merge_map WHERE status='same_id_review'"
        ).fetchone()[0]
        task_review = candidate.execute(
            "SELECT COUNT(*) FROM fusion_task_merge_map WHERE status='shared_review'"
        ).fetchone()[0]
        fk_preview = None
        if task_project_db:
            fk_preview = {
                "missing_before": candidate.execute("SELECT COUNT(*) FROM tasks WHERE project_id NOT IN (SELECT id FROM projects)").fetchone()[0],
                "missing_after": candidate.execute("SELECT COUNT(*) FROM fusion_tasks_fk_preview t LEFT JOIN fusion_projects_fk_preview p ON p.id=t.proposed_project_id WHERE p.id IS NULL").fetchone()[0],
            }
        graph_fk_preview = None
        if graph_fk_db:
            graph_fk_preview = {
                "nodes": candidate.execute("SELECT COUNT(*) FROM fusion_graph_nodes_fk_preview").fetchone()[0],
                "edges": candidate.execute("SELECT COUNT(*) FROM fusion_graph_edges_fk_preview").fetchone()[0],
                "quarantine": candidate.execute("SELECT COUNT(*) FROM fusion_graph_quarantine_preview").fetchone()[0],
                "foreign_key_violations": candidate.execute("SELECT COUNT(*) FROM fusion_graph_edges_fk_preview e LEFT JOIN fusion_graph_nodes_fk_preview s ON s.id=e.from_node LEFT JOIN fusion_graph_nodes_fk_preview t ON t.id=e.to_node WHERE s.id IS NULL OR t.id IS NULL").fetchone()[0],
            }
        candidate_integrity = candidate.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = _foreign_keys(candidate)
    blockers = []
    source_hashes = {name: _sha256(path) for name, path in sources.items()}
    if manifest is None or manifest[0] != "review_only" or manifest[2] != 0:
        blockers.append("candidate_manifest_invalid")
    elif json.loads(manifest[1]) != source_hashes:
        blockers.append("source_hash_mismatch")
    blockers.append("review_only_candidate")
    if any(not row["content_equal"] for row in application.values()):
        blockers.append("application_content_changed")
    if any(not row["count_equal"] for row in attached.values()):
        blockers.append("auxiliary_row_count_mismatch")
    if candidate_integrity != "ok":
        blockers.append("integrity_check_failed")
    if foreign_keys["error"] or foreign_keys["total"]:
        blockers.append("foreign_key_violations_or_error")
    if project_review or task_review or preview_status.get("unresolved", 0):
        blockers.append("unresolved_review_items")
    return {
        "report_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "review_only",
        "ready_for_cutover": not blockers,
        "blockers": blockers,
        "source_sha256": source_hashes,
        "candidate_sha256": _sha256(candidate_db),
        "application_tables": application,
        "attached_tables": attached,
        "graph_preview_status": preview_status,
        "project_review_required": project_review,
        "task_review_required": task_review,
        "task_project_fk_preview": fk_preview,
        "graph_fk_preview": graph_fk_preview,
        "integrity_check": candidate_integrity,
        "foreign_key_check": foreign_keys,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-db", type=Path, required=True)
    parser.add_argument("--mapping-db", type=Path, required=True)
    parser.add_argument("--graph-db", type=Path, required=True)
    parser.add_argument("--scheduler-db", type=Path, required=True)
    parser.add_argument("--candidate-db", type=Path, required=True)
    parser.add_argument("--task-project-db", type=Path)
    parser.add_argument("--graph-fk-db", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.base_db, args.mapping_db, args.graph_db, args.scheduler_db, args.candidate_db, args.task_project_db, args.graph_fk_db)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "ready_for_cutover", "blockers", "integrity_check", "foreign_key_check")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
