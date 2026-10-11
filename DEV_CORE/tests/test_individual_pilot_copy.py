"""The pilot works on a reconciled copy and keeps every legacy identity."""

import hashlib
import sqlite3

import pytest

from devcore_engine.db import connect_db
from Scripts.prepare_individual_pilot_copy import ARCHIVE_PROJECT, prepare
from Scripts.reconcile_sqlite_candidate import reconcile


def _reconciled_fixture(tmp_path):
    original = tmp_path / "original.db"
    reconciled = tmp_path / "reconciled.db"
    conn = connect_db(original)
    conn.execute("INSERT INTO projects(id,name,root_path) VALUES ('alpha','alpha','/alpha')")
    conn.execute("INSERT INTO kg_nodes(id,type,label) VALUES ('node-a','file','a')")
    conn.execute("INSERT INTO kg_nodes(id,type,label) VALUES ('node-b','file','b')")
    conn.execute("INSERT INTO kg_edges(from_node,to_node,type) VALUES ('node-a','node-b','valid')")
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.executemany(
        "INSERT INTO tasks(id,project_id,title) VALUES (?,?,?)",
        [("T-2", "alpha", "numeric"), ("T-02", "alpha", "collision"),
         ("slug", "alpha", "text"), ("T-00", "alpha", "zero"),
         ("T-1", "missing", "missing project")],
    )
    conn.execute("INSERT INTO kg_edges(from_node,to_node,type) VALUES ('node-a','lost','orphan')")
    conn.execute("PRAGMA user_version=1")
    conn.commit()
    conn.close()
    reconcile(original, reconciled)
    return reconciled


def test_pilot_preserves_reconciled_rows_and_assigns_unique_numbers(tmp_path):
    source = _reconciled_fixture(tmp_path)
    pilot = tmp_path / "pilot.db"
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()

    result = prepare(source, pilot)

    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    assert result["pilot_copy_ready"] is True
    assert result["operationally_qualified"] is False
    assert result["integrity"] == "ok"
    assert result["number_plan"] == {
        "preserved": 2, "allocated_collision": 1, "allocated_text": 1,
        "allocated_nonpositive": 1,
    }
    conn = sqlite3.connect(pilot)
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert conn.execute("SELECT count(*) FROM tasks").fetchone()[0] == 5
    assert conn.execute("SELECT count(*) FROM kg_edges").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM kg_edges_quarantine").fetchone()[0] == 1
    assert conn.execute("SELECT status FROM projects WHERE id=?", (ARCHIVE_PROJECT,)).fetchone()[0] == "needs_review"
    assert conn.execute("SELECT status FROM projects WHERE id='missing'").fetchone()[0] == "needs_review"
    assert conn.execute("SELECT name FROM sqlite_master WHERE name='knowledge_items'").fetchone()
    assert dict(conn.execute("""
        SELECT legacy_task_id,pilot_task_number FROM legacy_task_identity_map
        WHERE project_id='alpha'
    """)) == {"T-2": 2, "T-00": 3, "T-02": 4, "slug": 5}
    conn.close()


def test_pilot_refuses_existing_destination(tmp_path):
    source = _reconciled_fixture(tmp_path)
    destination = tmp_path / "keep.db"
    destination.write_bytes(b"keep")
    with pytest.raises(ValueError, match="must be new"):
        prepare(source, destination)
    assert destination.read_bytes() == b"keep"
