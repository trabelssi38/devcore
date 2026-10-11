"""The legacy importer must never discover an active data root implicitly."""

import json
import importlib.util
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "Scripts" / "migrate_json_to_sqlite.py"


def run_importer(tmp_path, *args):
    env = os.environ.copy()
    env.update(
        DEVCORE_LOCAL_ROOT=str(tmp_path / "local"),
        DEVCORE_DATA_ROOT=str(tmp_path / "shared"),
        DEVCORE_PLATFORM_ROOT=str(tmp_path / "platform"),
    )
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )


def test_source_and_destination_are_explicit_and_preview_is_read_only(tmp_path):
    source = tmp_path / "copy"
    task_file = source / "Memory" / "alpha" / "tasks.json"
    task_file.parent.mkdir(parents=True)
    task_file.write_text(json.dumps({"tasks": [{"id": "T-1", "title": "Copied"}]}), encoding="utf-8")
    shared_summary = tmp_path / "shared" / "Logs" / "token_reports" / "token_metrics_summary.json"
    shared_summary.parent.mkdir(parents=True)
    shared_summary.write_text(json.dumps({"sessions": [{"tokens": 999}]}), encoding="utf-8")
    original_summary = shared_summary.read_bytes()

    rejected = run_importer(tmp_path)
    assert rejected.returncode != 0
    assert "--source-root" in rejected.stderr
    assert not (tmp_path / "shared" / "devcore.db").exists()

    preview = run_importer(tmp_path, "--source-root", source, "--dry-run")
    assert preview.returncode == 0, preview.stderr
    assert "Tasks found: 1" in preview.stdout
    assert "Token metrics found: 0" in preview.stdout
    assert not list(tmp_path.rglob("*.db"))

    destination = tmp_path / "imported.db"
    imported = run_importer(tmp_path, "--source-root", source, "--destination-db", destination)
    assert imported.returncode == 0, imported.stderr
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT project, title FROM tasks").fetchall() == [("alpha", "Copied")]
        assert db.execute("SELECT count(*) FROM token_calls").fetchone()[0] == 0
    rerun = run_importer(tmp_path, "--source-root", source, "--destination-db", destination)
    assert rerun.returncode != 0
    assert "FileExistsError" in rerun.stderr
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT count(*) FROM tasks").fetchone()[0] == 1
    assert shared_summary.read_bytes() == original_summary
    assert not (tmp_path / "shared" / "devcore.db").exists()


def test_token_summary_requires_explicit_file_and_verify_does_not_write(tmp_path):
    source = tmp_path / "copy"
    source.mkdir()
    summary = source / "legacy-token-summary.json"
    summary.write_text(json.dumps({"sessions": [{"model": "example", "tokens": 7}]}), encoding="utf-8")
    destination = tmp_path / "imported.db"

    imported = run_importer(tmp_path, "--source-root", source, "--destination-db", destination,
                            "--token-summary", summary)
    assert imported.returncode == 0, imported.stderr
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT model, tokens FROM token_calls").fetchall() == [("example", 7)]

    before = destination.read_bytes()
    verified = run_importer(tmp_path, "--verify", "--destination-db", destination)
    assert verified.returncode == 0, verified.stderr
    assert "Table 'token_calls': 1 record(s)" in verified.stdout
    assert destination.read_bytes() == before


def test_malformed_explicit_token_summary_fails_without_false_success(tmp_path):
    source = tmp_path / "copy"
    source.mkdir()
    summary = source / "broken.json"
    summary.write_text("{broken", encoding="utf-8")
    preview = run_importer(tmp_path, "--source-root", source, "--token-summary", summary, "--dry-run")
    assert preview.returncode != 0
    assert "Invalid token summary" in preview.stderr
    assert "Migration finished successfully" not in preview.stdout
    assert not list(tmp_path.rglob("*.db"))


def test_malformed_task_or_event_is_rejected_before_database_creation(tmp_path):
    source = tmp_path / "copy"
    tasks = source / "Memory" / "alpha" / "tasks.json"
    tasks.parent.mkdir(parents=True)
    tasks.write_text("{bad", encoding="utf-8")
    destination = tmp_path / "imported.db"

    rejected = run_importer(tmp_path, "--source-root", source, "--destination-db", destination)
    assert rejected.returncode != 0
    assert "Invalid tasks file" in rejected.stderr
    assert not destination.exists()

    tasks.write_text('{"tasks": []}', encoding="utf-8")
    event = source / "Bus" / "events" / "bad.json"
    event.parent.mkdir(parents=True)
    event.write_text("{bad", encoding="utf-8")
    rejected = run_importer(tmp_path, "--source-root", source, "--destination-db", destination)
    assert rejected.returncode != 0
    assert "Invalid event file" in rejected.stderr
    assert not destination.exists()


def test_import_rolls_back_all_categories_when_later_insert_fails(tmp_path, monkeypatch):
    source = tmp_path / "copy"
    source.mkdir()
    destination = tmp_path / "imported.db"

    tasks = source / "Memory" / "alpha" / "tasks.json"
    tasks.parent.mkdir(parents=True)
    tasks.write_text(json.dumps({"tasks": [{"id": "T-1", "title": "Copied"}]}), encoding="utf-8")
    event = source / "Bus" / "events" / "one.json"
    event.parent.mkdir(parents=True)
    event.write_text(json.dumps({"event_type": "copied"}), encoding="utf-8")
    summary = source / "tokens.json"
    summary.write_text(json.dumps({"sessions": [{"model": "example", "tokens": 7}]}), encoding="utf-8")

    spec = importlib.util.spec_from_file_location("legacy_json_migration_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.migrate_tokens

    def fail_on_insert(db, file, dry_run=False, row_digest=None):
        if dry_run:
            return original(db, file, dry_run=True)
        raise RuntimeError("late insert failure")

    monkeypatch.setattr(module, "migrate_tokens", fail_on_insert)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--source-root", str(source),
                                   "--destination-db", str(destination), "--token-summary", str(summary)])
    with pytest.raises(RuntimeError, match="late insert failure"):
        module.main()
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT count(*) FROM tasks").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM events").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM token_calls").fetchone()[0] == 0


def test_existing_empty_database_is_not_opened_or_modified(tmp_path):
    source = tmp_path / "copy"
    source.mkdir()
    destination = tmp_path / "existing.db"
    destination.write_bytes(b"existing fixture bytes")
    before = destination.read_bytes()
    rejected = run_importer(tmp_path, "--source-root", source, "--destination-db", destination)
    assert rejected.returncode != 0
    assert "FileExistsError" in rejected.stderr
    assert destination.read_bytes() == before


def test_silent_count_divergence_rolls_back_before_success(tmp_path, monkeypatch):
    source = tmp_path / "copy"
    source.mkdir()
    event = source / "Bus" / "events" / "one.json"
    event.parent.mkdir(parents=True)
    event.write_text(json.dumps({"event_type": "copied"}), encoding="utf-8")
    destination = tmp_path / "imported.db"

    spec = importlib.util.spec_from_file_location("legacy_json_migration_count_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.migrate_events

    def falsely_count_event(db, root, dry_run=False, row_digest=None):
        if dry_run:
            return original(db, root, dry_run=True)
        return 1  # Emulate a future adapter reporting an inserted row without writing it.

    monkeypatch.setattr(module, "migrate_events", falsely_count_event)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--source-root", str(source),
                                   "--destination-db", str(destination)])
    with pytest.raises(ValueError, match="Migration count mismatch"):
        module.main()
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT count(*) FROM events").fetchone()[0] == 0


def test_source_change_with_same_count_rolls_back(tmp_path, monkeypatch):
    source = tmp_path / "copy"
    tasks = source / "Memory" / "alpha" / "tasks.json"
    tasks.parent.mkdir(parents=True)
    tasks.write_text(json.dumps({"tasks": [{"id": "T-1", "title": "Before"}]}), encoding="utf-8")
    destination = tmp_path / "imported.db"

    spec = importlib.util.spec_from_file_location("legacy_json_migration_drift_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.migrate_tasks

    def change_after_insert(db, root, dry_run=False, row_digest=None):
        result = original(db, root, dry_run=dry_run, row_digest=row_digest)
        if not dry_run:
            tasks.write_text(json.dumps({"tasks": [{"id": "T-1", "title": "After"}]}), encoding="utf-8")
        return result

    monkeypatch.setattr(module, "migrate_tasks", change_after_insert)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--source-root", str(source),
                                   "--destination-db", str(destination)])
    with pytest.raises(ValueError, match="Source files changed"):
        module.main()
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT count(*) FROM tasks").fetchone()[0] == 0


def test_content_change_in_sqlite_with_same_count_rolls_back(tmp_path, monkeypatch):
    source = tmp_path / "copy"
    tasks = source / "Memory" / "alpha" / "tasks.json"
    tasks.parent.mkdir(parents=True)
    tasks.write_text(json.dumps({"tasks": [{"id": "T-1", "title": "Expected"}]}), encoding="utf-8")
    destination = tmp_path / "imported.db"

    spec = importlib.util.spec_from_file_location("legacy_json_migration_content_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.init_db

    def install_mutating_trigger(db):
        original(db)
        db.execute("""CREATE TRIGGER alter_task AFTER INSERT ON tasks
                      BEGIN UPDATE tasks SET title='Altered' WHERE id=NEW.id AND project=NEW.project; END""")

    monkeypatch.setattr(module, "init_db", install_mutating_trigger)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--source-root", str(source),
                                   "--destination-db", str(destination)])
    with pytest.raises(ValueError, match="Migration content mismatch: tasks"):
        module.main()
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT count(*) FROM tasks").fetchone()[0] == 0


def test_content_reconciliation_accepts_two_projects_with_same_task_id(tmp_path):
    source = tmp_path / "copy"
    for project, title in (("beta", "B"), ("alpha", "A")):
        task_file = source / "Memory" / project / "tasks.json"
        task_file.parent.mkdir(parents=True)
        task_file.write_text(json.dumps({"project": project, "tasks": [
            {"id": "T-1", "title": title, "steps": [{"text": title}], "status": "pending"}
        ]}), encoding="utf-8")
    event = source / "Bus" / "events" / "one.json"
    event.parent.mkdir(parents=True)
    event.write_text(json.dumps({"event_type": "copied", "timestamp": "2026-10-09T00:00:00Z"}), encoding="utf-8")
    summary = source / "tokens.json"
    summary.write_text(json.dumps({"sessions": [{"model": "example", "tokens": 9,
                                                  "timestamp": "2026-10-09T00:00:00Z"}]}), encoding="utf-8")
    destination = tmp_path / "imported.db"
    imported = run_importer(tmp_path, "--source-root", source, "--destination-db", destination,
                            "--token-summary", summary)
    assert imported.returncode == 0, imported.stderr
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT project, id, title FROM tasks ORDER BY project, id").fetchall() == [
            ("alpha", "T-1", "A"), ("beta", "T-1", "B")]
        assert db.execute("SELECT count(*) FROM events").fetchone()[0] == 1
        assert db.execute("SELECT tokens FROM token_calls").fetchone()[0] == 9


@pytest.mark.parametrize("board", [
    {"tasks": [{"title": "missing id"}]},
    {"tasks": [{"id": "T-1"}, {"id": "T-1"}]},
    {"project": "beta", "tasks": [{"id": "T-1"}]},
    {"tasks": [{"id": "T-1", "project": "beta"}]},
    {"tasks": "not a list"},
])
def test_invalid_or_cross_project_tasks_fail_before_database_creation(tmp_path, board):
    source = tmp_path / "copy"
    tasks = source / "Memory" / "alpha" / "tasks.json"
    tasks.parent.mkdir(parents=True)
    tasks.write_text(json.dumps(board), encoding="utf-8")
    destination = tmp_path / "imported.db"
    rejected = run_importer(tmp_path, "--source-root", source, "--destination-db", destination)
    assert rejected.returncode != 0
    assert "Invalid tasks file" in rejected.stderr
    assert not destination.exists()


def test_invalid_event_and_token_rows_fail_before_database_creation(tmp_path):
    source = tmp_path / "copy"
    source.mkdir()
    destination = tmp_path / "imported.db"
    event = source / "Bus" / "events" / "one.json"
    event.parent.mkdir(parents=True)
    event.write_text("[]", encoding="utf-8")
    rejected = run_importer(tmp_path, "--source-root", source, "--destination-db", destination)
    assert rejected.returncode != 0
    assert "Invalid event file" in rejected.stderr
    assert not destination.exists()

    event.write_text("{}", encoding="utf-8")
    summary = source / "tokens.json"
    summary.write_text(json.dumps({"sessions": [None]}), encoding="utf-8")
    rejected = run_importer(tmp_path, "--source-root", source, "--destination-db", destination,
                            "--token-summary", summary)
    assert rejected.returncode != 0
    assert "Invalid token summary" in rejected.stderr
    assert not destination.exists()

