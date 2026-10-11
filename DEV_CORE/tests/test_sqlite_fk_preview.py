"""The migration preview must preserve data and leave the source untouched."""

import hashlib
import sqlite3

import pytest

from devcore_engine.db import connect_db
from Scripts.preview_sqlite_fk_migration import preview


def test_preview_repairs_legacy_task_fk_without_touching_source(tmp_path):
    source = tmp_path / "source.db"
    candidate = tmp_path / "candidate.db"
    conn = connect_db(source)
    conn.execute("INSERT INTO projects(id,name,root_path) VALUES ('alpha','alpha','/alpha')")
    conn.execute("INSERT INTO tasks(id,project_id,title) VALUES ('T-01','alpha','task')")
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("DROP TABLE runs")
    conn.execute("""
        CREATE TABLE runs (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id),
            task_id TEXT REFERENCES _legacy_tasks(id),
            status TEXT NOT NULL DEFAULT 'queued', runner TEXT,
            started_at TEXT, finished_at TEXT, metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("INSERT INTO runs(id,project_id,task_id) VALUES ('legacy','alpha','T-01')")
    conn.commit()
    conn.close()

    old_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    result = preview(source, candidate)
    assert result["ready_for_cutover"]
    assert result["integrity"] == "ok"
    assert result["source_schema_version"] == 0
    assert result["candidate_schema_version"] == 1
    assert result["preserved_rows"]["runs"] == 1
    assert hashlib.sha256(source.read_bytes()).hexdigest() == old_hash

    migrated = sqlite3.connect(candidate)
    migrated.execute("PRAGMA foreign_keys=ON")
    assert migrated.execute("PRAGMA user_version").fetchone()[0] == 1
    fk = migrated.execute("PRAGMA foreign_key_list(runs)").fetchall()
    assert {(row[3], row[4]) for row in fk if row[2] == "tasks"} == {
        ("task_id", "id"), ("project_id", "project_id")
    }
    migrated.execute("INSERT INTO runs(id,project_id,task_id) VALUES ('r1','alpha','T-01')")
    with pytest.raises(sqlite3.IntegrityError):
        migrated.execute("INSERT INTO runs(id,project_id,task_id) VALUES ('r2','alpha','T-02')")
    migrated.close()


def test_preview_refuses_overwrite(tmp_path):
    source = tmp_path / "source.db"
    connect_db(source).close()
    with pytest.raises(ValueError):
        preview(source, source)
    existing = tmp_path / "existing.db"
    existing.write_bytes(b"keep")
    with pytest.raises(ValueError):
        preview(source, existing)
    assert existing.read_bytes() == b"keep"


def test_preview_handles_older_knowledge_tables_without_project_id(tmp_path):
    source = tmp_path / "old.db"
    candidate = tmp_path / "fk-preview.db"
    conn = connect_db(source)
    conn.execute("DROP INDEX idx_kg_nodes_project")
    conn.execute("DROP INDEX idx_kg_edges_project")
    conn.execute("DROP INDEX idx_vault_notes_project")
    for table in ("kg_nodes", "kg_edges", "vault_notes"):
        conn.execute(f"ALTER TABLE {table} DROP COLUMN project_id")
    conn.execute("INSERT INTO projects(id,name,root_path) VALUES ('alpha','alpha','/alpha')")
    conn.execute("INSERT INTO tasks(id,project_id,title) VALUES ('T-01','alpha','task')")
    conn.commit()
    conn.close()

    old_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    result = preview(source, candidate)
    assert result["integrity"] == "ok"
    assert result["ready_for_cutover"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == old_hash
    migrated = sqlite3.connect(candidate)
    assert migrated.execute("PRAGMA user_version").fetchone()[0] == 1
    assert "project_id" not in {row[1] for row in migrated.execute("PRAGMA table_info(kg_nodes)")}
    assert migrated.execute("PRAGMA foreign_key_check").fetchall() == []
    migrated.close()
