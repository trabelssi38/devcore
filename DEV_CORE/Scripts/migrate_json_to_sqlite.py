#!/usr/bin/env python3
# migrate_json_to_sqlite.py -- DEV_CORE v10 JSON to SQLite Migration
# Migrates file-based state (tasks.json, events, token calls, workflows) into devcore.db (SQLite WAL)

import json
import sqlite3
import argparse
import hashlib
from contextlib import closing
from pathlib import Path
from datetime import datetime

def init_db(db_conn):
    db_conn.execute("PRAGMA journal_mode=WAL;")
    db_conn.execute("PRAGMA synchronous=NORMAL;")
    
    # Create tables
    db_conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT,
            project TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            mode TEXT,
            steps_total INTEGER DEFAULT 0,
            steps_done INTEGER DEFAULT 0,
            source TEXT,
            details TEXT,
            started_at TEXT,
            completed_at TEXT,
            PRIMARY KEY (id, project)
        );
    """)
    db_conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project);")
    db_conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")

    db_conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            source TEXT,
            tool_name TEXT,
            duration REAL DEFAULT 0.0,
            success INTEGER DEFAULT 1,
            payload TEXT
        );
    """)
    db_conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);")

    db_conn.execute("""
        CREATE TABLE IF NOT EXISTS token_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            model TEXT NOT NULL,
            tokens INTEGER DEFAULT 0,
            cache_hits INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0.0,
            task_id TEXT
        );
    """)
    db_conn.execute("CREATE INDEX IF NOT EXISTS idx_token_calls_ts ON token_calls(timestamp);")

    db_conn.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            state TEXT,
            created_at TEXT,
            updated_at TEXT
        );
    """)

    db_conn.execute("""
        CREATE TABLE IF NOT EXISTS service_status (
            name TEXT PRIMARY KEY,
            host TEXT NOT NULL,
            port INTEGER NOT NULL,
            is_up INTEGER DEFAULT 0,
            last_check TEXT
        );
    """)
    db_conn.commit()

def digest_row(digest, row):
    if digest is not None:
        digest.update(json.dumps(tuple(row), ensure_ascii=False, allow_nan=False).encode("utf-8"))
        digest.update(b"\n")


def migrate_tasks(db_conn, source_root, dry_run=False, row_digest=None):
    memory_dir = source_root / "Memory"
    if not memory_dir.exists():
        return 0
    
    task_count = 0
    for proj_dir in sorted(memory_dir.iterdir(), key=lambda path: path.name.encode("utf-8")):
        if not proj_dir.is_dir():
            continue
        tasks_file = proj_dir / "tasks.json"
        if not tasks_file.exists():
            continue
        
        project_name = proj_dir.name
        try:
            with open(tasks_file, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            if isinstance(data, dict):
                if data.get("project", project_name) != project_name:
                    raise ValueError("board project differs from its directory")
                task_list = data.get("tasks")
            else:
                task_list = data
            if not isinstance(task_list, list):
                raise ValueError("tasks must be a list")
            seen_ids = set()
            for index, t in enumerate(task_list):
                if not isinstance(t, dict) or not isinstance(t.get("id"), (str, int)) or not str(t["id"]).strip():
                    raise ValueError(f"task at index {index} has no valid id")
                if t.get("project", project_name) != project_name:
                    raise ValueError(f"task at index {index} belongs to another project")
                task_id = str(t["id"])
                if task_id in seen_ids:
                    raise ValueError(f"duplicate task id {task_id}")
                seen_ids.add(task_id)
            for t in sorted(task_list, key=lambda item: str(item["id"])):
                task_id = str(t["id"])
                title = str(t.get("title", t.get("name", "Untitled")))
                status = str(t.get("status", "pending"))
                mode = str(t.get("mode", "coding"))
                steps_list = t.get("steps") if isinstance(t.get("steps"), list) else []
                steps_total = int(t.get("steps_total", len(steps_list)))
                steps_done = int(t.get("steps_done", 0))
                source = str(t.get("source", "user"))
                details = json.dumps(steps_list, ensure_ascii=False) if steps_list else str(t.get("details", ""))
                started_at = str(t.get("started_at", t.get("created_at", "")))
                completed_at = str(t.get("completed_at", ""))
                row = (task_id, project_name, title, status, mode, steps_total,
                       steps_done, source, details, started_at, completed_at)
                
                if not dry_run:
                    db_conn.execute("""
                        INSERT OR REPLACE INTO tasks 
                        (id, project, title, status, mode, steps_total, steps_done, source, details, started_at, completed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, row)
                    digest_row(row_digest, row)
                task_count += 1
        except Exception as e:
            raise ValueError(f"Invalid tasks file {tasks_file}: {e}") from e
            
    return task_count

def migrate_events(db_conn, source_root, dry_run=False, row_digest=None):
    events_dir = source_root / "Bus" / "events"
    if not events_dir.exists():
        return 0
    
    event_count = 0
    for evt_file in sorted(events_dir.glob("*.json"), key=lambda path: path.name.encode("utf-8")):
        try:
            with open(evt_file, "r", encoding="utf-8-sig") as f:
                evt = json.load(f)
            if not isinstance(evt, dict):
                raise ValueError("event must be an object")
            
            event_type = str(evt.get("event_type", evt.get("type", "unknown")))
            timestamp = str(evt.get("timestamp", evt.get("time", datetime.now().isoformat())))
            source = str(evt.get("source", "system"))
            tool_name = str(evt.get("tool_name", evt.get("tool", "")))
            duration = float(evt.get("duration", 0.0))
            success = 1 if evt.get("success", True) else 0
            payload = json.dumps(evt, ensure_ascii=False)
            row = (event_type, timestamp, source, tool_name, duration, success, payload)
            
            if not dry_run:
                db_conn.execute("""
                    INSERT INTO events (event_type, timestamp, source, tool_name, duration, success, payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, row)
                digest_row(row_digest, row)
            event_count += 1
        except Exception as e:
            raise ValueError(f"Invalid event file {evt_file}: {e}") from e
            
    return event_count

def migrate_tokens(db_conn, summary_file, dry_run=False, row_digest=None):
    token_count = 0
    if summary_file is not None and summary_file.exists():
        try:
            with open(summary_file, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            
            sessions = data.get("sessions") if isinstance(data, dict) else data
            if not isinstance(sessions, list):
                raise ValueError("sessions must be a list")
            for index, s in enumerate(sessions):
                if not isinstance(s, dict):
                    raise ValueError(f"session at index {index} must be an object")
                timestamp = str(s.get("timestamp", s.get("date", datetime.now().isoformat())))
                model = str(s.get("model", "unknown"))
                tokens = int(s.get("total_tokens", s.get("tokens", 0)))
                cache_hits = int(s.get("cache_hits", 0))
                output_tokens = int(s.get("output_tokens", 0))
                cost_usd = float(s.get("cost_usd", s.get("cost", 0.0)))
                task_id = str(s.get("task_id", ""))
                row = (timestamp, model, tokens, cache_hits, output_tokens, cost_usd, task_id)
                
                if not dry_run:
                    db_conn.execute("""
                        INSERT INTO token_calls (timestamp, model, tokens, cache_hits, output_tokens, cost_usd, task_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, row)
                    digest_row(row_digest, row)
                token_count += 1
        except Exception as e:
            raise ValueError(f"Invalid token summary {summary_file}: {e}") from e
            
    return token_count

def verify_migration(db_conn):
    print("\n--- SQLite Verification Report ---")
    tables = ["tasks", "events", "token_calls", "workflows", "service_status"]
    counts = {}
    for tbl in tables:
        cur = db_conn.execute(f"SELECT count(*) FROM {tbl}")
        count = cur.fetchone()[0]
        counts[tbl] = count
        print(f"Table '{tbl}': {count} record(s)")
    print("----------------------------------\n")
    return counts


def require_matching_counts(db_conn, expected, imported):
    tables = ("tasks", "events", "token_calls")
    stored = tuple(db_conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in tables)
    if expected != imported or imported != stored:
        raise ValueError(f"Migration count mismatch: expected={expected}, imported={imported}, stored={stored}")


def require_matching_content(db_conn, imported_digests):
    queries = (
        "SELECT id, project, title, status, mode, steps_total, steps_done, source, details, started_at, completed_at FROM tasks ORDER BY project, id",
        "SELECT event_type, timestamp, source, tool_name, duration, success, payload FROM events ORDER BY id",
        "SELECT timestamp, model, tokens, cache_hits, output_tokens, cost_usd, task_id FROM token_calls ORDER BY id",
    )
    for table, query, expected in zip(("tasks", "events", "token_calls"), queries, imported_digests):
        stored = hashlib.sha256()
        for row in db_conn.execute(query):
            digest_row(stored, row)
        if stored.digest() != expected.digest():
            raise ValueError(f"Migration content mismatch: {table}")


def source_fingerprint(source_root, summary_file):
    paths = []
    memory_dir = source_root / "Memory"
    if memory_dir.is_dir():
        paths.extend(path / "tasks.json" for path in memory_dir.iterdir()
                     if path.is_dir() and (path / "tasks.json").is_file())
    events_dir = source_root / "Bus" / "events"
    if events_dir.is_dir():
        paths.extend(events_dir.glob("*.json"))
    if summary_file is not None:
        paths.append(summary_file)
    fingerprints = []
    for path in sorted(paths):
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        fingerprints.append((str(path.resolve()), digest.hexdigest()))
    return tuple(fingerprints)

def main():
    parser = argparse.ArgumentParser(description="Legacy JSON import into an explicitly selected SQLite database")
    parser.add_argument("--source-root", type=Path, help="Explicit root of a copied legacy JSON snapshot")
    parser.add_argument("--destination-db", type=Path, help="Explicit destination SQLite file")
    parser.add_argument("--token-summary", type=Path, help="Explicit legacy token summary to import")
    parser.add_argument("--dry-run", action="store_true", help="Count source records without opening or creating a database")
    parser.add_argument("--verify", action="store_true", help="Read counts from an existing destination database")
    args = parser.parse_args()

    if args.verify:
        if args.dry_run or args.source_root or args.token_summary or not args.destination_db:
            parser.error("--verify requires only --destination-db")
        db_path = args.destination_db.resolve(strict=True)
        with closing(sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)) as db_conn:
            verify_migration(db_conn)
        return

    if not args.source_root or not args.source_root.is_dir():
        parser.error("--source-root must name an existing copied snapshot")
    if args.dry_run and args.destination_db:
        parser.error("--dry-run does not accept --destination-db")
    if not args.dry_run and not args.destination_db:
        parser.error("--destination-db is required for an import")
    if args.token_summary and not args.token_summary.is_file():
        parser.error("--token-summary must name an existing file")
    source_root = args.source_root.resolve(strict=True)
    summary_file = args.token_summary.resolve(strict=True) if args.token_summary else None

    print(f"[migrate] Starting migration (dry_run={args.dry_run})...")
    if args.dry_run:
        print(f"[migrate] Tasks found: {migrate_tasks(None, source_root, dry_run=True)}")
        print(f"[migrate] Events found: {migrate_events(None, source_root, dry_run=True)}")
        print(f"[migrate] Token metrics found: {migrate_tokens(None, summary_file, dry_run=True)}")
    else:
        # Reject malformed sources before creating a destination database.
        source_before = source_fingerprint(source_root, summary_file)
        expected = (
            migrate_tasks(None, source_root, dry_run=True),
            migrate_events(None, source_root, dry_run=True),
            migrate_tokens(None, summary_file, dry_run=True),
        )
        db_path = args.destination_db.resolve()
        # Exclusive creation prevents this legacy importer from opening an
        # existing database, even one that currently contains no rows.
        with db_path.open("xb"):
            pass
        print(f"[migrate] Connecting to SQLite DB: {db_path}")
        with closing(sqlite3.connect(db_path)) as db_conn:
            init_db(db_conn)
            try:
                db_conn.execute("BEGIN IMMEDIATE")
                row_digests = (hashlib.sha256(), hashlib.sha256(), hashlib.sha256())
                task_count = migrate_tasks(db_conn, source_root, row_digest=row_digests[0])
                event_count = migrate_events(db_conn, source_root, row_digest=row_digests[1])
                token_count = migrate_tokens(db_conn, summary_file, row_digest=row_digests[2])
                require_matching_counts(db_conn, expected, (task_count, event_count, token_count))
                require_matching_content(db_conn, row_digests)
                if source_fingerprint(source_root, summary_file) != source_before:
                    raise ValueError("Source files changed during migration")
                db_conn.commit()
            except Exception:
                db_conn.rollback()
                raise
            print(f"[migrate] Tasks migrated: {task_count}")
            print(f"[migrate] Events migrated: {event_count}")
            print(f"[migrate] Token metrics migrated: {token_count}")
            verify_migration(db_conn)
    print("[migrate] Migration finished successfully.")

if __name__ == "__main__":
    main()
