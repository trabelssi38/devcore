"""Build a disposable SQLite copy with repaired task foreign keys.

This command never opens the source database for writing. Existing orphan rows
are reported and retained for explicit reconciliation rather than deleted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from devcore_engine.db import INIT_SCHEMA_SQL  # noqa: E402

CHILD_TABLES = ("runs", "events", "audit_log")
MIGRATION_VERSION = 1


def table_digest(conn: sqlite3.Connection, table: str) -> str:
    digest = hashlib.sha256()
    for row in conn.execute(f'SELECT * FROM "{table}" ORDER BY id'):
        digest.update(json.dumps(tuple(row), ensure_ascii=False, default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def canonical_definitions() -> dict[str, str]:
    reference = sqlite3.connect(":memory:")
    try:
        reference.executescript(INIT_SCHEMA_SQL)
        return {
            table: reference.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()[0]
            for table in CHILD_TABLES
        }
    finally:
        reference.close()


def preview(source_path: Path, destination_path: Path) -> dict:
    source_path = source_path.resolve(strict=True)
    destination_path = destination_path.resolve()
    if source_path == destination_path or destination_path.exists():
        raise ValueError("destination must be a new path distinct from source")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(f"file:{source_path.as_posix()}?mode=ro", uri=True)
    target = sqlite3.connect(destination_path)
    try:
        source.backup(target)
        source_version = source.execute("PRAGMA user_version").fetchone()[0]
        if source_version > MIGRATION_VERSION:
            raise RuntimeError(f"unsupported newer SQLite schema version: {source_version}")
        before = {table: (source.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0],
                          table_digest(source, table)) for table in CHILD_TABLES}
        definitions = canonical_definitions()
        child_objects = {
            table: [row[0] for row in source.execute(
                "SELECT sql FROM sqlite_master WHERE tbl_name=? "
                "AND type IN ('index', 'trigger') AND sql IS NOT NULL ORDER BY type, name",
                (table,))]
            for table in CHILD_TABLES
        }
        target.execute("PRAGMA foreign_keys=OFF")
        target.execute("BEGIN IMMEDIATE")
        for table in CHILD_TABLES:
            columns = [row[1] for row in target.execute(f'PRAGMA table_info("{table}")')]
            new_name = f"__migration_{table}"
            ddl = definitions[table].replace(f"CREATE TABLE {table}", f'CREATE TABLE "{new_name}"', 1)
            target.execute(ddl)
            names = ", ".join(f'"{name}"' for name in columns)
            target.execute(f'INSERT INTO "{new_name}" ({names}) SELECT {names} FROM "{table}"')
            target.execute(f'DROP TABLE "{table}"')
            target.execute(f'ALTER TABLE "{new_name}" RENAME TO "{table}"')
            for ddl in child_objects[table]:
                target.execute(ddl)
        target.commit()
        # The source may predate project_id on knowledge tables. Replaying the
        # entire current schema would build indexes against columns that are
        # intentionally left for a later, separately reviewed migration.
        target.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_project_identity "
                       "ON tasks(id, project_id)")
        target.execute(f"PRAGMA user_version={MIGRATION_VERSION}")
        after = {table: (target.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0],
                         table_digest(target, table)) for table in CHILD_TABLES}
        if before != after:
            raise RuntimeError("row counts or content changed in a migrated child table")
        integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")
        violations = Counter((row[0], row[2]) for row in target.execute("PRAGMA foreign_key_check"))
        result = {
            "source": str(source_path), "candidate": str(destination_path),
            "source_schema_version": source_version,
            "candidate_schema_version": MIGRATION_VERSION,
            "integrity": integrity,
            "preserved_rows": {table: before[table][0] for table in CHILD_TABLES},
            "foreign_key_violations": [
                {"table": child, "parent": parent, "count": count}
                for (child, parent), count in sorted(violations.items())
            ],
            "ready_for_cutover": not violations,
        }
        return result
    except Exception:
        target.close()
        destination_path.unlink(missing_ok=True)
        raise
    finally:
        source.close()
        try:
            target.close()
        except Exception:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(preview(args.source, args.destination), indent=2, ensure_ascii=False))
