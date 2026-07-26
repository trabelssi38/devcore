#!/usr/bin/env python3
# migrate_json_to_sqlite.py -- DEV_CORE v10 JSON to SQLite Migration
# Migrates file-based state (tasks.json, events, token calls, workflows) into devcore.db (SQLite WAL)

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

DATA_ROOT = Path(os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[3] / "DEV_CORE_DATA")))
DB_PATH = DATA_ROOT / "devcore.db"

def init_db(db_conn):
    db_conn.execute("PRAGMA journal_mode=WAL;")
    db_conn.execute("PRAGMA synchronous=NORMAL;")
    
    # Create tables
    db_conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            project TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            mode TEXT,
            steps_total INTEGER DEFAULT 0,
            steps_done INTEGER DEFAULT 0,
            source TEXT,
            details TEXT,
            started_at TEXT,
            completed_at TEXT
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

def migrate_tasks(db_conn, dry_run=False):
    memory_dir = DATA_ROOT / "Memory"
    if not memory_dir.exists():
        return 0
    
    task_count = 0
    for proj_dir in memory_dir.iterdir():
        if not proj_dir.is_dir():
            continue
        tasks_file = proj_dir / "tasks.json"
        if not tasks_file.exists():
            continue
        
        project_name = proj_dir.name
        try:
            with open(tasks_file, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            
            task_list = data.get("tasks", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            for t in task_list:
                if not isinstance(t, dict) or "id" not in t:
                    continue
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
                
                if not dry_run:
                    db_conn.execute("""
                        INSERT OR REPLACE INTO tasks 
                        (id, project, title, status, mode, steps_total, steps_done, source, details, started_at, completed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (task_id, project_name, title, status, mode, steps_total, steps_done, source, details, started_at, completed_at))
                task_count += 1
        except Exception as e:
            print(f"[migrate] Error reading {tasks_file}: {e}")
            
    if not dry_run:
        db_conn.commit()
    return task_count

def migrate_events(db_conn, dry_run=False):
    events_dir = DATA_ROOT / "Bus" / "events"
    if not events_dir.exists():
        return 0
    
    event_count = 0
    for evt_file in events_dir.glob("*.json"):
        try:
            with open(evt_file, "r", encoding="utf-8-sig") as f:
                evt = json.load(f)
            if not isinstance(evt, dict):
                continue
            
            event_type = str(evt.get("event_type", evt.get("type", "unknown")))
            timestamp = str(evt.get("timestamp", evt.get("time", datetime.now().isoformat())))
            source = str(evt.get("source", "system"))
            tool_name = str(evt.get("tool_name", evt.get("tool", "")))
            duration = float(evt.get("duration", 0.0))
            success = 1 if evt.get("success", True) else 0
            payload = json.dumps(evt, ensure_ascii=False)
            
            if not dry_run:
                db_conn.execute("""
                    INSERT INTO events (event_type, timestamp, source, tool_name, duration, success, payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (event_type, timestamp, source, tool_name, duration, success, payload))
            event_count += 1
        except Exception as e:
            print(f"[migrate] Error reading event {evt_file}: {e}")
            
    if not dry_run:
        db_conn.commit()
    return event_count

def migrate_tokens(db_conn, dry_run=False):
    summary_file = DATA_ROOT / "Logs" / "token_reports" / "token_metrics_summary.json"
    token_count = 0
    if summary_file.exists():
        try:
            with open(summary_file, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            
            sessions = data.get("sessions", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            for s in sessions:
                if not isinstance(s, dict):
                    continue
                timestamp = str(s.get("timestamp", s.get("date", datetime.now().isoformat())))
                model = str(s.get("model", "unknown"))
                tokens = int(s.get("total_tokens", s.get("tokens", 0)))
                cache_hits = int(s.get("cache_hits", 0))
                output_tokens = int(s.get("output_tokens", 0))
                cost_usd = float(s.get("cost_usd", s.get("cost", 0.0)))
                task_id = str(s.get("task_id", ""))
                
                if not dry_run:
                    db_conn.execute("""
                        INSERT INTO token_calls (timestamp, model, tokens, cache_hits, output_tokens, cost_usd, task_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (timestamp, model, tokens, cache_hits, output_tokens, cost_usd, task_id))
                token_count += 1
        except Exception as e:
            print(f"[migrate] Error reading token metrics {summary_file}: {e}")
            
    if not dry_run:
        db_conn.commit()
    return token_count

def verify_migration(db_conn):
    print("\n--- SQLite Verification Report ---")
    tables = ["tasks", "events", "token_calls", "workflows", "service_status"]
    for tbl in tables:
        cur = db_conn.execute(f"SELECT count(*) FROM {tbl}")
        count = cur.fetchone()[0]
        print(f"Table '{tbl}': {count} record(s)")
    print("----------------------------------\n")

def main():
    parser = argparse.ArgumentParser(description="DEV_CORE JSON to SQLite Migration Tool")
    parser.add_argument("--dry-run", action="store_true", help="Preview migration without modifying DB")
    parser.add_argument("--verify", action="store_true", help="Verify DB record counts")
    args = parser.parse_args()

    print(f"[migrate] Connecting to SQLite DB: {DB_PATH}")
    db_conn = sqlite3.connect(DB_PATH)
    init_db(db_conn)

    if args.verify:
        verify_migration(db_conn)
        db_conn.close()
        return

    print(f"[migrate] Starting migration (dry_run={args.dry_run})...")
    t_cnt = migrate_tasks(db_conn, dry_run=args.dry_run)
    print(f"[migrate] Tasks migrated: {t_cnt}")

    e_cnt = migrate_events(db_conn, dry_run=args.dry_run)
    print(f"[migrate] Events migrated: {e_cnt}")

    tk_cnt = migrate_tokens(db_conn, dry_run=args.dry_run)
    print(f"[migrate] Token metrics migrated: {tk_cnt}")

    verify_migration(db_conn)
    db_conn.close()
    print("[migrate] Migration finished successfully.")

if __name__ == "__main__":
    main()
