"""The version migration operates on a disposable copy and preserves task data."""

import hashlib
import sqlite3

import pytest

from devcore_engine.db import connect_db, init_db
from Scripts.preview_task_version_migration import preview


def test_task_version_candidate_preserves_source_and_detects_stale_writer(tmp_path):
    source = tmp_path / "source.db"
    candidate = tmp_path / "candidate.db"
    conn = connect_db(source)
    conn.execute("INSERT INTO projects(id,name,root_path) VALUES ('alpha','alpha','/alpha')")
    conn.execute("INSERT INTO tasks(id,project_id,title) VALUES ('T-01','alpha','original')")
    conn.commit()
    conn.execute("DROP TRIGGER tasks_increment_version")
    conn.execute("ALTER TABLE tasks DROP COLUMN version")
    conn.execute("PRAGMA user_version=1")
    conn.commit()
    conn.close()

    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    result = preview(source, candidate)
    assert result["ready_for_cutover"]
    assert result["candidate_schema_version"] == 2
    assert result["preserved_tasks"] == 1
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash

    migrated = connect_db(candidate)
    task = migrated.execute("SELECT title,version FROM tasks WHERE id='T-01'").fetchone()
    assert (task["title"], task["version"]) == ("original", 1)
    migrated.execute("UPDATE tasks SET title='changed' WHERE id='T-01' AND project_id='alpha'")
    migrated.commit()
    assert migrated.execute("SELECT version FROM tasks WHERE id='T-01'").fetchone()[0] == 2
    migrated.close()


def test_task_version_candidate_refuses_to_overwrite(tmp_path):
    source = tmp_path / "source.db"
    connect_db(source).close()
    existing = tmp_path / "existing.db"
    existing.write_bytes(b"keep")
    with pytest.raises(ValueError):
        preview(source, existing)
    assert existing.read_bytes() == b"keep"


def test_init_db_repairs_project_scoped_tasks_for_post_commit_hook(tmp_path):
    db = tmp_path / "legacy.db"
    conn = connect_db(db)
    conn.execute("INSERT INTO projects(id,name,root_path) VALUES ('alpha','alpha','/alpha')")
    conn.execute("INSERT INTO tasks(id,project_id,title) VALUES ('T-01','alpha','session')")
    conn.commit()
    conn.execute("DROP TRIGGER tasks_increment_version")
    conn.execute("ALTER TABLE tasks DROP COLUMN version")
    conn.commit()
    conn.close()

    migrated = init_db(db)
    task = migrated.execute(
        "SELECT title,version FROM tasks WHERE id='T-01' AND project_id='alpha'"
    ).fetchone()
    assert (task["title"], task["version"]) == ("session", 1)
    migrated.execute(
        "UPDATE tasks SET title='commit' WHERE id='T-01' AND project_id='alpha'"
    )
    migrated.commit()
    assert migrated.execute(
        "SELECT version FROM tasks WHERE id='T-01' AND project_id='alpha'"
    ).fetchone()[0] == 2
    migrated.close()


def test_init_db_migrates_oldest_task_shape_before_hook_indexes(tmp_path):
    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT NOT NULL, "
        "status TEXT NOT NULL DEFAULT 'todo', steps_done INTEGER NOT NULL DEFAULT 0, "
        "steps_total INTEGER NOT NULL DEFAULT 1, project TEXT, started_at TEXT, completed_at TEXT)"
    )
    conn.execute("INSERT INTO tasks(id,title,project) VALUES ('T-01','session','alpha')")
    conn.commit()
    conn.close()

    migrated = init_db(db)
    row = migrated.execute(
        "SELECT project_id,version FROM tasks WHERE id='T-01'"
    ).fetchone()
    assert (row["project_id"], row["version"]) == ("alpha", 1)
    migrated.close()
