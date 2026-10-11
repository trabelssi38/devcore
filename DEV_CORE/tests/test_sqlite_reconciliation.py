"""Candidate reconciliation preserves history while isolating invalid edges."""

import hashlib
import sqlite3
from pathlib import Path

import pytest

from devcore_engine.db import connect_db
from Scripts.reconcile_sqlite_candidate import legacy_task_uuid, reconcile


def test_candidate_reconciles_without_deleting_history(tmp_path):
    source = tmp_path / "source.db"
    target = tmp_path / "review.db"
    conn = connect_db(source)
    conn.execute("INSERT INTO projects(id,name,root_path) VALUES ('known','known','/known')")
    conn.execute("INSERT INTO kg_nodes(id,type,label) VALUES ('node-a','file','a')")
    conn.execute("INSERT INTO kg_nodes(id,type,label) VALUES ('node-b','file','b')")
    conn.execute("INSERT INTO kg_edges(from_node,to_node,type) VALUES ('node-a','node-b','valid')")
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("INSERT INTO tasks(id,project_id,title) VALUES ('T-01','missing','orphan task')")
    conn.execute("INSERT INTO kg_edges(from_node,to_node,type) VALUES ('node-a','lost','broken')")
    conn.execute("INSERT INTO kg_edges(from_node,to_node,type) VALUES ('lost','also-lost','broken')")
    conn.execute("PRAGMA user_version=1")
    conn.commit()
    conn.close()

    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    result = reconcile(source, target)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    assert result["integrity"] == "ok"
    assert result["placeholder_projects"] == ["missing"]
    assert result["foreign_key_violations"] == []
    assert result["candidate_counts"]["kg_edges"] == 1
    assert result["candidate_counts"]["kg_edges_quarantine"] == 2
    assert result["quarantine_reasons"] == {
        "both_nodes_missing": 1,
        "target_node_missing": 1,
    }
    assert result["review_required"]
    assert not result["ready_for_cutover"]
    assert result["content_digests"]["tasks_source"] == result["content_digests"]["tasks_candidate"]
    assert result["content_digests"]["edges_source"] == result["content_digests"]["edges_candidate_with_quarantine"]

    candidate = sqlite3.connect(target)
    candidate.execute("PRAGMA foreign_keys=ON")
    assert candidate.execute("PRAGMA foreign_key_check").fetchall() == []
    assert candidate.execute(
        "SELECT status FROM projects WHERE id='missing'"
    ).fetchone()[0] == "needs_review"
    assert candidate.execute("SELECT id FROM tasks WHERE project_id='missing'").fetchone()
    candidate.close()


def test_candidate_records_global_task_mapping_and_unresolved_references(tmp_path):
    source = tmp_path / "source.db"
    target = tmp_path / "review.db"
    conn = connect_db(source)
    conn.execute("INSERT INTO projects(id,name,root_path) VALUES ('alpha','alpha','/alpha')")
    conn.execute("INSERT INTO projects(id,name,root_path) VALUES ('beta','beta','/beta')")
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.executemany(
        "INSERT INTO tasks(id,project_id,title,depends_on) VALUES (?, ?, ?, ?)",
        [
            ("T-1", "alpha", "alpha root", None),
            ("T-1", "beta", "beta root", None),
            ("T-2", "alpha", "resolved dependency", "T-1"),
            ("T-3", "alpha", "missing dependency", "T-99"),
        ],
    )
    conn.executemany(
        """INSERT INTO events(id,project_id,task_id,event_type,source)
           VALUES (?, ?, ?, 'legacy', 'fixture')""",
        [
            ("event-resolved", "alpha", "T-1"),
            ("event-missing", "alpha", "T-99"),
            ("event-ambiguous", "unknown", "T-1"),
        ],
    )
    conn.execute("PRAGMA user_version=1")
    conn.commit()
    conn.close()

    result = reconcile(source, target)

    assert result["candidate_counts"]["legacy_task_identity_map"] == 4
    assert result["candidate_counts"]["legacy_task_reference_report"] == 5
    assert result["task_reference_resolutions"] == {
        "ambiguous_project": 1,
        "missing": 2,
        "resolved": 2,
    }
    assert result["review_required"]

    candidate = sqlite3.connect(target)
    assert candidate.execute("""
        SELECT task_uuid FROM legacy_task_identity_map
        WHERE project_id='alpha' AND legacy_task_id='T-1'
    """).fetchone()[0] == legacy_task_uuid("alpha", "T-1")
    assert candidate.execute("""
        SELECT resolution, candidate_project_ids FROM legacy_task_reference_report
        WHERE source_table='events' AND project_id='unknown' AND legacy_task_id='T-1'
    """).fetchone() == ("ambiguous_project", '["alpha", "beta"]')
    candidate.close()


def test_candidate_refuses_to_overwrite(tmp_path):
    source = tmp_path / "source.db"
    connect_db(source).close()
    with pytest.raises(ValueError):
        reconcile(source, source)
    target = tmp_path / "existing.db"
    target.write_bytes(b"keep")
    with pytest.raises(ValueError):
        reconcile(source, target)
    assert target.read_bytes() == b"keep"


def test_candidate_creation_race_preserves_foreign_file(tmp_path, monkeypatch):
    source = tmp_path / "source.db"
    connect_db(source).close()
    target = tmp_path / "review.db"
    original_open = Path.open

    def create_foreign_file(path, mode="r", *args, **kwargs):
        if path == target and mode == "xb":
            with original_open(path, "wb") as stream:
                stream.write(b"foreign file")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", create_foreign_file)
    with pytest.raises(FileExistsError):
        reconcile(source, target)
    assert target.read_bytes() == b"foreign file"


def test_failed_candidate_is_preserved_for_review(tmp_path):
    source = tmp_path / "source.db"
    target = tmp_path / "review.db"
    conn = connect_db(source)
    conn.execute("PRAGMA user_version=99")
    conn.commit()
    conn.close()
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()

    with pytest.raises(RuntimeError, match="expected SQLite FK preview version"):
        reconcile(source, target)
    assert target.exists()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash


def test_candidate_assigns_task_number_and_detects_collisions(tmp_path):
    source = tmp_path / "source.db"
    target = tmp_path / "review.db"
    conn = connect_db(source)
    conn.execute("INSERT INTO projects(id,name,root_path) VALUES ('alpha','alpha','/alpha')")
    conn.execute("INSERT INTO projects(id,name,root_path) VALUES ('beta','beta','/beta')")
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.executemany(
        "INSERT INTO tasks(id,project_id,title) VALUES (?, ?, ?)",
        [
            ("T-1", "alpha", "alpha first"),
            ("T-01", "alpha", "alpha leading zero collision"),
            ("T-2", "alpha", "alpha unique second"),
            ("custom_slug", "alpha", "non numeric task"),
            ("T-1", "beta", "beta first unique in beta"),
        ],
    )
    conn.execute("PRAGMA user_version=1")
    conn.commit()
    conn.close()

    result = reconcile(source, target)
    assert result["task_number_resolutions"] == {
        "collision": 2,
        "parsed": 2,
        "unparseable": 1,
    }
    assert result["review_required"] is True

    candidate = sqlite3.connect(target)
    alpha_rows = candidate.execute("""
        SELECT legacy_task_id, task_number, number_status
        FROM legacy_task_identity_map
        WHERE project_id='alpha'
        ORDER BY legacy_task_id
    """).fetchall()
    assert alpha_rows == [
        ("T-01", 1, "collision"),
        ("T-1", 1, "collision"),
        ("T-2", 2, "parsed"),
        ("custom_slug", None, "unparseable"),
    ]

    beta_row = candidate.execute("""
        SELECT legacy_task_id, task_number, number_status
        FROM legacy_task_identity_map
        WHERE project_id='beta'
    """).fetchone()
    assert beta_row == ("T-1", 1, "parsed")
    candidate.close()


def test_candidate_classifies_runtime_state_into_preferences_and_ephemeral(tmp_path):
    source = tmp_path / "source.db"
    target = tmp_path / "review.db"
    conn = connect_db(source)
    conn.execute("INSERT INTO projects(id,name,root_path) VALUES ('proj1','proj1','/p')")
    conn.executemany(
        "INSERT INTO runtime_state(key, value) VALUES (?, ?)",
        [
            ("active_client", "codex"),
            ("theme", "dark"),
            ("project.auto_lint", "true"),
            ("active_project", "proj1"),
            ("last_sync", "2026-10-10T00:00:00"),
            ("lock_daemon", "pid-1234"),
            ("unknown_experimental_flag", "enabled"),
        ],
    )
    conn.execute("PRAGMA user_version=1")
    conn.commit()
    conn.close()

    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    result = reconcile(source, target)

    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    assert result["candidate_counts"]["legacy_runtime_state_report"] == 7
    assert result["runtime_state_classifications"] == {
        "ambiguous_needs_review": 1,
        "ephemeral_to_rebuild": 3,
        "preference_to_migrate": 3,
    }
    assert result["review_required"] is True
    assert (
        result["content_digests"]["runtime_state_source"]
        == result["content_digests"]["runtime_state_candidate"]
    )

    candidate = sqlite3.connect(target)
    report_rows = dict(candidate.execute(
        "SELECT key, classification || ':' || target_scope FROM legacy_runtime_state_report"
    ).fetchall())
    assert report_rows == {
        "active_client": "preference_to_migrate:user_preference",
        "theme": "preference_to_migrate:user_preference",
        "project.auto_lint": "preference_to_migrate:project_preference",
        "active_project": "ephemeral_to_rebuild:ephemeral",
        "last_sync": "ephemeral_to_rebuild:ephemeral",
        "lock_daemon": "ephemeral_to_rebuild:ephemeral",
        "unknown_experimental_flag": "ambiguous_needs_review:needs_review",
    }
    # Verify runtime_state itself remains untouched in candidate
    preserved_runtime = candidate.execute(
        "SELECT count(*) FROM runtime_state"
    ).fetchone()[0]
    assert preserved_runtime == 7
    candidate.close()
