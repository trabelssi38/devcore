"""Build a review-only SQLite candidate with orphan references isolated.

The source is opened read-only and copied with SQLite's online backup API.
No row is discarded: dangling graph edges move to a quarantine table, while
missing task projects become clearly marked placeholder records.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import hashlib
import uuid
from collections import Counter
from pathlib import Path


def digest_rows(rows) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps(tuple(row), ensure_ascii=False).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


TASK_REFERENCE_TABLES = ("runs", "events", "audit_log", "task_imports")
TASK_UUID_NAMESPACE = uuid.UUID("3bbec48a-1d88-524e-b9da-55e57b23a3c7")


def legacy_task_uuid(project_id: str, task_id: str) -> str:
    """Return the stable global identity proposed for a legacy task pair."""
    return str(uuid.uuid5(TASK_UUID_NAMESPACE, f"{project_id}\x00{task_id}"))


def parse_task_number(legacy_task_id: str) -> int | None:
    """Extract numeric suffix from task identifiers like T-01, T-1, task-42."""
    match = re.match(r"^(?:T-|task-)?(\d+)$", legacy_task_id.strip(), re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def classify_runtime_state_entry(key: str, value: str) -> tuple[str, str, str]:
    """Classify a legacy runtime_state row into target disposition.

    Returns (classification, target_scope, notes).
    """
    k = key.strip().lower()
    # Ephemeral states to rebuild
    if k in ("active_project", "active_task", "current_session", "active_session"):
        return (
            "ephemeral_to_rebuild",
            "ephemeral",
            f"Global {key} from legacy runtime; replaced by explicit RequestContext or dynamic session state.",
        )
    if k.startswith(("last_", "tmp_", "lock_", "heartbeat_")):
        return (
            "ephemeral_to_rebuild",
            "ephemeral",
            f"Transient timestamp or process lock ({key}); rebuilt at runtime.",
        )
    # User / client preferences to migrate
    if k == "active_client":
        return (
            "preference_to_migrate",
            "user_preference",
            "Active client tool preference; migrate to user profile.",
        )
    if k in ("theme", "ui_mode") or k.startswith(("ui_", "dashboard_")):
        return (
            "preference_to_migrate",
            "user_preference",
            f"UI display preference ({key}); migrate to user interface settings.",
        )
    if k.startswith(("config.", "settings.")):
        return (
            "preference_to_migrate",
            "user_preference",
            f"Configuration setting ({key}); migrate to application config.",
        )
    if k.startswith(("project.", "project_pref.")):
        return (
            "preference_to_migrate",
            "project_preference",
            f"Project-scoped setting ({key}); migrate to project metadata.",
        )
    return (
        "ambiguous_needs_review",
        "needs_review",
        f"Unrecognized runtime_state key '{key}'; requires explicit operator review.",
    )


def build_runtime_state_report(candidate: sqlite3.Connection) -> Counter:
    """Classify legacy runtime_state keys as preferences to migrate or ephemeral state."""
    candidate.execute("""
        CREATE TABLE legacy_runtime_state_report (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            classification TEXT NOT NULL CHECK (
                classification IN ('preference_to_migrate', 'ephemeral_to_rebuild', 'ambiguous_needs_review')
            ),
            target_scope TEXT NOT NULL CHECK (
                target_scope IN ('user_preference', 'project_preference', 'ephemeral', 'needs_review')
            ),
            notes TEXT NOT NULL DEFAULT ''
        )
    """)
    has_runtime_state = candidate.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_state'"
    ).fetchone()
    if not has_runtime_state:
        return Counter()

    rows = candidate.execute(
        "SELECT key, value FROM runtime_state ORDER BY key"
    ).fetchall()
    classified_rows = []
    classifications: Counter = Counter()
    for key, value in rows:
        classification, target_scope, notes = classify_runtime_state_entry(key, value)
        classifications[classification] += 1
        classified_rows.append((key, value, classification, target_scope, notes))

    candidate.executemany(
        """INSERT INTO legacy_runtime_state_report
           (key, value, classification, target_scope, notes)
           VALUES (?, ?, ?, ?, ?)""",
        classified_rows,
    )
    return classifications


def build_task_reference_report(candidate: sqlite3.Connection) -> tuple[Counter, Counter]:
    """Persist a reviewable mapping without rewriting legacy task references.

    The current candidate remains a SQLite review copy.  This table records
    the deterministic UUID proposed for every ``(project_id, task_id)`` pair
    and reports references that cannot be mapped unambiguously.  A later
    PostgreSQL migration can consume this table without guessing again.
    """
    candidate.execute("""
        CREATE TABLE legacy_task_identity_map (
            project_id TEXT NOT NULL,
            legacy_task_id TEXT NOT NULL,
            task_uuid TEXT NOT NULL UNIQUE,
            task_number INTEGER,
            number_status TEXT NOT NULL CHECK (
                number_status IN ('parsed', 'collision', 'unparseable')
            ),
            PRIMARY KEY (project_id, legacy_task_id)
        )
    """)
    candidate.execute("""
        CREATE TABLE legacy_task_reference_report (
            source_table TEXT NOT NULL,
            source_rowid INTEGER NOT NULL,
            project_id TEXT NOT NULL,
            legacy_task_id TEXT NOT NULL,
            resolution TEXT NOT NULL CHECK (
                resolution IN ('resolved', 'missing', 'ambiguous_project')
            ),
            task_uuid TEXT,
            candidate_project_ids TEXT NOT NULL DEFAULT '[]',
            PRIMARY KEY (source_table, source_rowid)
        )
    """)
    task_rows = candidate.execute(
        "SELECT project_id, id FROM tasks ORDER BY project_id, id"
    ).fetchall()

    project_tasks: dict[str, list[str]] = {}
    for project_id, task_id in task_rows:
        project_tasks.setdefault(project_id, []).append(task_id)

    task_number_resolutions: Counter = Counter()
    identity_rows = []
    for project_id, task_id in task_rows:
        task_uuid = legacy_task_uuid(project_id, task_id)
        parsed = parse_task_number(task_id)
        if parsed is None:
            status = "unparseable"
            num = None
        else:
            matches = [
                tid for tid in project_tasks[project_id]
                if parse_task_number(tid) == parsed
            ]
            if len(matches) > 1:
                status = "collision"
                num = parsed
            else:
                status = "parsed"
                num = parsed
        task_number_resolutions[status] += 1
        identity_rows.append((project_id, task_id, task_uuid, num, status))

    candidate.executemany(
        """INSERT INTO legacy_task_identity_map
           (project_id, legacy_task_id, task_uuid, task_number, number_status)
           VALUES (?, ?, ?, ?, ?)""",
        identity_rows,
    )

    mappings = {
        (project_id, task_id): task_uuid
        for project_id, task_id, task_uuid in candidate.execute(
            "SELECT project_id, legacy_task_id, task_uuid FROM legacy_task_identity_map"
        )
    }
    projects_by_task_id: dict[str, list[str]] = {}
    for project_id, task_id in mappings:
        projects_by_task_id.setdefault(task_id, []).append(project_id)

    def report_reference(source_table: str, rowid: int, project_id: str, task_id: str) -> str:
        task_uuid = mappings.get((project_id, task_id))
        candidate_projects = sorted(projects_by_task_id.get(task_id, ()))
        resolution = "resolved" if task_uuid else (
            "ambiguous_project" if candidate_projects else "missing"
        )
        candidate.execute("""
            INSERT INTO legacy_task_reference_report
                (source_table, source_rowid, project_id, legacy_task_id,
                 resolution, task_uuid, candidate_project_ids)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            source_table, rowid, project_id, task_id, resolution, task_uuid,
            json.dumps(candidate_projects, ensure_ascii=False),
        ))
        return resolution

    resolutions: Counter = Counter()
    for rowid, project_id, task_id in candidate.execute("""
        SELECT rowid, project_id, depends_on FROM tasks
        WHERE depends_on IS NOT NULL AND trim(depends_on) <> ''
        ORDER BY project_id, id
    """):
        resolutions[report_reference("tasks.depends_on", rowid, project_id, task_id)] += 1
    for table in TASK_REFERENCE_TABLES:
        exists = candidate.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            continue
        for rowid, project_id, task_id in candidate.execute(
            f"SELECT rowid, project_id, task_id FROM {table} "
            "WHERE task_id IS NOT NULL AND trim(task_id) <> '' ORDER BY rowid"
        ):
            resolutions[report_reference(table, rowid, project_id, task_id)] += 1
    return resolutions, task_number_resolutions


def reconcile(source_path: Path, destination_path: Path) -> dict:
    source_path = source_path.resolve(strict=True)
    destination_path = destination_path.resolve()
    if source_path == destination_path or destination_path.exists():
        raise ValueError("destination must be a new path distinct from source")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(f"file:{source_path.as_posix()}?mode=ro", uri=True)
    candidate = None
    try:
        # Fail if another process created the destination after the check.
        # A failed candidate remains for inspection; never unlink a path that
        # could have been replaced by another process.
        with destination_path.open("xb"):
            pass
        candidate = sqlite3.connect(destination_path)
        source.backup(candidate)
        source_version = source.execute("PRAGMA user_version").fetchone()[0]
        if source_version != 1:
            raise RuntimeError(f"expected SQLite FK preview version 1, got {source_version}")
        source_counts = {
            table: source.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("projects", "tasks", "kg_nodes", "kg_edges")
        }
        has_source_runtime = source.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_state'"
        ).fetchone()
        source_runtime_digest = ""
        if has_source_runtime:
            source_runtime_digest = digest_rows(
                source.execute("SELECT key, value FROM runtime_state ORDER BY key")
            )
        source_tasks_digest = digest_rows(source.execute("SELECT * FROM tasks ORDER BY project_id, id"))
        source_edge_columns = [row[1] for row in source.execute("PRAGMA table_info(kg_edges)")]
        if "project_id" in source_edge_columns:
            source_edges_digest = digest_rows(source.execute(
                "SELECT id, project_id, from_node, to_node, type, properties "
                "FROM kg_edges ORDER BY id"))
        else:
            source_edges_digest = digest_rows(source.execute(
                "SELECT id, from_node, to_node, type, properties FROM kg_edges ORDER BY id"))
        candidate.execute("PRAGMA foreign_keys=ON")
        candidate.execute("BEGIN IMMEDIATE")
        missing_projects = candidate.execute("""
            SELECT DISTINCT t.project_id FROM tasks t
            LEFT JOIN projects p ON p.id = t.project_id
            WHERE p.id IS NULL ORDER BY t.project_id
        """).fetchall()
        for (project_id,) in missing_projects:
            candidate.execute("""
                INSERT INTO projects (id, name, root_path, status, metadata)
                VALUES (?, ?, '[unresolved]', 'needs_review', ?)
            """, (project_id, project_id, json.dumps({
                "reconciliation": "placeholder_for_existing_tasks"
            })))

        has_project_id = "project_id" in [
            row[1] for row in candidate.execute("PRAGMA table_info(kg_edges)").fetchall()
        ]
        if has_project_id:
            candidate.execute("""
                CREATE TABLE kg_edges_quarantine (
                    id INTEGER PRIMARY KEY,
                    project_id TEXT,
                    from_node TEXT NOT NULL,
                    to_node TEXT NOT NULL,
                    type TEXT NOT NULL,
                    properties TEXT,
                    reason TEXT NOT NULL
                )
            """)
            candidate.execute("""
                INSERT INTO kg_edges_quarantine
                    (id, project_id, from_node, to_node, type, properties, reason)
                SELECT e.id, e.project_id, e.from_node, e.to_node, e.type, e.properties,
                    CASE
                        WHEN src.id IS NULL AND dst.id IS NULL THEN 'both_nodes_missing'
                        WHEN src.id IS NULL THEN 'source_node_missing'
                        ELSE 'target_node_missing'
                    END
                FROM kg_edges e
                LEFT JOIN kg_nodes src ON src.id = e.from_node
                LEFT JOIN kg_nodes dst ON dst.id = e.to_node
                WHERE src.id IS NULL OR dst.id IS NULL
            """)
        else:
            candidate.execute("""
                CREATE TABLE kg_edges_quarantine (
                    id INTEGER PRIMARY KEY,
                    from_node TEXT NOT NULL,
                    to_node TEXT NOT NULL,
                    type TEXT NOT NULL,
                    properties TEXT,
                    reason TEXT NOT NULL
                )
            """)
            candidate.execute("""
                INSERT INTO kg_edges_quarantine
                    (id, from_node, to_node, type, properties, reason)
                SELECT e.id, e.from_node, e.to_node, e.type, e.properties,
                    CASE
                        WHEN src.id IS NULL AND dst.id IS NULL THEN 'both_nodes_missing'
                        WHEN src.id IS NULL THEN 'source_node_missing'
                        ELSE 'target_node_missing'
                    END
                FROM kg_edges e
                LEFT JOIN kg_nodes src ON src.id = e.from_node
                LEFT JOIN kg_nodes dst ON dst.id = e.to_node
                WHERE src.id IS NULL OR dst.id IS NULL
            """)
        candidate.execute("DELETE FROM kg_edges WHERE id IN (SELECT id FROM kg_edges_quarantine)")
        reference_resolutions, task_number_resolutions = build_task_reference_report(candidate)
        runtime_state_classifications = build_runtime_state_report(candidate)
        candidate.commit()

        quarantined = candidate.execute(
            "SELECT reason, count(*) FROM kg_edges_quarantine GROUP BY reason ORDER BY reason"
        ).fetchall()
        violations = Counter((row[0], row[2]) for row in candidate.execute(
            "PRAGMA foreign_key_check"
        ))
        integrity = candidate.execute("PRAGMA integrity_check").fetchone()[0]
        tasks_digest = digest_rows(candidate.execute("SELECT * FROM tasks ORDER BY project_id, id"))
        if has_project_id:
            edges_digest = digest_rows(candidate.execute("""
                SELECT id, project_id, from_node, to_node, type, properties FROM (
                    SELECT id, project_id, from_node, to_node, type, properties FROM kg_edges
                    UNION ALL
                    SELECT id, project_id, from_node, to_node, type, properties FROM kg_edges_quarantine
                ) ORDER BY id
            """))
        else:
            edges_digest = digest_rows(candidate.execute("""
                SELECT id, from_node, to_node, type, properties FROM (
                    SELECT id, from_node, to_node, type, properties FROM kg_edges
                    UNION ALL
                    SELECT id, from_node, to_node, type, properties FROM kg_edges_quarantine
                ) ORDER BY id
            """))
        candidate_runtime_digest = ""
        if has_source_runtime:
            candidate_runtime_digest = digest_rows(
                candidate.execute("SELECT key, value FROM runtime_state ORDER BY key")
            )
        result = {
            "source": str(source_path),
            "candidate": str(destination_path),
            "source_schema_version": source_version,
            "integrity": integrity,
            "source_counts": source_counts,
            "candidate_counts": {
                table: candidate.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in (
                    *source_counts,
                    "kg_edges_quarantine",
                    "legacy_task_identity_map",
                    "legacy_task_reference_report",
                    "legacy_runtime_state_report",
                )
            },
            "content_digests": {
                "tasks_source": source_tasks_digest,
                "tasks_candidate": tasks_digest,
                "edges_source": source_edges_digest,
                "edges_candidate_with_quarantine": edges_digest,
                **({
                    "runtime_state_source": source_runtime_digest,
                    "runtime_state_candidate": candidate_runtime_digest,
                } if has_source_runtime else {}),
            },
            "placeholder_projects": [row[0] for row in missing_projects],
            "quarantine_reasons": dict(quarantined),
            "task_reference_resolutions": dict(sorted(reference_resolutions.items())),
            "task_number_resolutions": dict(sorted(task_number_resolutions.items())),
            "runtime_state_classifications": dict(sorted(runtime_state_classifications.items())),
            "foreign_key_violations": [
                {"table": child, "parent": parent, "count": count}
                for (child, parent), count in sorted(violations.items())
            ],
            "ready_for_cutover": False,
            "review_required": bool(
                missing_projects or quarantined or violations
                or reference_resolutions["missing"]
                or reference_resolutions["ambiguous_project"]
                or task_number_resolutions["collision"]
                or task_number_resolutions["unparseable"]
                or runtime_state_classifications.get("ambiguous_needs_review", 0) > 0
            ),
        }
        if (integrity != "ok"
                or result["candidate_counts"]["tasks"] != source_counts["tasks"]
                or result["candidate_counts"]["kg_nodes"] != source_counts["kg_nodes"]
                or result["candidate_counts"]["kg_edges"]
                + result["candidate_counts"]["kg_edges_quarantine"] != source_counts["kg_edges"]
                or (has_source_runtime and candidate_runtime_digest != source_runtime_digest)
                or tasks_digest != source_tasks_digest
                or edges_digest != source_edges_digest):
            raise RuntimeError("candidate integrity or row conservation check failed")
        return result
    finally:
        source.close()
        if candidate is not None:
            candidate.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(reconcile(args.source, args.destination), indent=2, ensure_ascii=False))
