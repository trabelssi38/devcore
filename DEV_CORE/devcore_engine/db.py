"""
db.py -- Unified SQLite Database Manager for DEV_CORE
Manages devcore.db connection, schema migrations, FTS5, and sqlite-vec vector tables.
"""

from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from typing import Any, Optional

os.environ["SQLITE_VEC_NO_WARN"] = "1"
try:
    import sqlite_vec
    HAS_SQLITE_VEC = True
except ImportError:
    HAS_SQLITE_VEC = False


def get_data_root() -> Path:
    env_root = os.getenv("DEVCORE_DATA_ROOT")
    if env_root:
        return Path(env_root)

    # Auto-detect Dropbox folder on Windows
    if os.name == "nt":
        app_data = os.getenv("APPDATA")
        if app_data:
            db_json = Path(app_data) / "Dropbox" / "info.json"
            if db_json.exists():
                try:
                    import json
                    with open(db_json, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    db_path = data.get("personal", {}).get("path")
                    if db_path:
                        g_path = Path(db_path) / "DEV_CORE_DATA"
                        if g_path.exists():
                            # Export it to env var so child processes inherit it
                            os.environ["DEVCORE_DATA_ROOT"] = str(g_path)
                            return g_path
                except Exception:
                    pass

    # Default fallback: parent of DEV_CORE directory / DEV_CORE_DATA
    platform_root = os.getenv("DEVCORE_PLATFORM_ROOT", "C:/devcore/DEV_CORE")
    return Path(platform_root).parent / "DEV_CORE_DATA"


def get_db_path() -> Path:
    data_root = get_data_root()
    data_root.mkdir(parents=True, exist_ok=True)
    return data_root / "devcore.db"


def connect_db(db_path: Optional[Path] = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = get_db_path()
    else:
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(db_path), timeout=30.0)

    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row

    if HAS_SQLITE_VEC:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

    conn.executescript(INIT_SCHEMA_SQL)

    return conn



INIT_SCHEMA_SQL = """
-- ============================================================
-- DEV_CORE Unified SQLite Schema
-- ============================================================

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    root_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Tasks
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'coding',
    status TEXT NOT NULL DEFAULT 'todo',
    steps_done INTEGER NOT NULL DEFAULT 0,
    steps_total INTEGER NOT NULL DEFAULT 1,
    depends_on TEXT REFERENCES tasks(id),
    worktree TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    started_at TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (steps_done >= 0 AND steps_total >= 1),
    CHECK (steps_done <= steps_total)
);

-- Runs
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    runner TEXT,
    started_at TEXT,
    finished_at TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Plugins (OLTP)
CREATE TABLE IF NOT EXISTS plugins (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    version TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (project_id, name)
);

-- Events (OLTP)
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
    run_id TEXT REFERENCES runs(id) ON DELETE SET NULL,
    plugin_id TEXT REFERENCES plugins(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    correlation_id TEXT,
    payload TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Audit Log
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
    run_id TEXT REFERENCES runs(id) ON DELETE SET NULL,
    plugin_id TEXT REFERENCES plugins(id) ON DELETE SET NULL,
    actor TEXT NOT NULL DEFAULT 'system',
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Schedules
CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    cron TEXT NOT NULL,
    timezone TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    next_run_at TEXT,
    last_run_at TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (status IN ('active', 'paused', 'disabled'))
);

-- Schedule History
CREATE TABLE IF NOT EXISTS schedule_history (
    id TEXT PRIMARY KEY,
    schedule_id TEXT NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    run_id TEXT REFERENCES runs(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    status TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '{}',
    occurred_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Outbox Messages
CREATE TABLE IF NOT EXISTS outbox_messages (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    idempotency_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    available_at TEXT NOT NULL DEFAULT (datetime('now')),
    processed_at TEXT
);

-- Memory Entries (L0-L3 persona, decisions, lessons, patterns, scenarios)
CREATE TABLE IF NOT EXISTS memory_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    task_type TEXT DEFAULT 'devcore',
    content TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_name_type ON memory_entries(name, task_type);

-- Knowledge Graph Nodes
CREATE TABLE IF NOT EXISTS kg_nodes (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    label TEXT NOT NULL,
    properties TEXT DEFAULT '{}'
);

-- Knowledge Graph Edges
CREATE TABLE IF NOT EXISTS kg_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_node TEXT NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE,
    to_node TEXT NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    properties TEXT DEFAULT '{}'
);

-- Bus Events
CREATE TABLE IF NOT EXISTS bus_events (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'devcore',
    event_type TEXT NOT NULL,
    project TEXT,
    task_id TEXT,
    correlation_id TEXT,
    payload TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_bus_events_date ON bus_events(created_at DESC);

-- Vault Notes (Obsidian PKM / Daily Notes)
CREATE TABLE IF NOT EXISTS vault_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    title TEXT,
    tags TEXT DEFAULT '[]',
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Workflow States
CREATE TABLE IF NOT EXISTS workflow_states (
    id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Plugins Registry
CREATE TABLE IF NOT EXISTS plugins_registry (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    metadata TEXT DEFAULT '{}',
    installed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Skills Runtime
CREATE TABLE IF NOT EXISTS skills_runtime (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'discovered',
    metadata TEXT DEFAULT '{}',
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Metrics
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    project TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT DEFAULT 'count',
    payload TEXT DEFAULT '{}',
    recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_metrics_source_date ON metrics(source, recorded_at DESC);

-- System Config
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    format TEXT DEFAULT 'json',
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Runtime State
CREATE TABLE IF NOT EXISTS runtime_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Conversations
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    task_id TEXT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- FTS5 Full-Text Search on Conversations
CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts USING fts5(
    project, task_id, content,
    content=conversations, content_rowid=id
);

-- Indices for OLTP tables
CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON tasks(project_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_task_status ON runs(task_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_project_created ON events(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_project_created ON audit_log(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_schedules_project_status ON schedules(project_id, status, next_run_at ASC);
CREATE INDEX IF NOT EXISTS idx_outbox_messages_status ON outbox_messages(status, created_at ASC);
"""

VECTOR_SCHEMA_SQL = """
-- Vector Tables via sqlite-vec (768 dimensions for gemini-embedding-001)
CREATE VIRTUAL TABLE IF NOT EXISTS vec_decisions USING vec0(
    embedding float[768],
    +id TEXT,
    +preview TEXT,
    +source TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS vec_lessons USING vec0(
    embedding float[768],
    +id TEXT,
    +preview TEXT,
    +source TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS vec_patterns USING vec0(
    embedding float[768],
    +id TEXT,
    +preview TEXT,
    +source TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS vec_codebase USING vec0(
    embedding float[768],
    +id TEXT,
    +preview TEXT,
    +file_path TEXT
);
"""


def _align_existing_schema(conn: sqlite3.Connection) -> None:
    """Migrate or align existing legacy tables if present by reconstructing them cleanly."""
    cursor = conn.cursor()
    
    # Align 'tasks' table
    table_info = cursor.execute("PRAGMA table_info(tasks);").fetchall()
    cols = {row[1]: row for row in table_info}
    if cols and ("project_id" not in cols or "updated_at" not in cols):
        cursor.execute("ALTER TABLE tasks RENAME TO _legacy_tasks;")
        cursor.execute("""
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL DEFAULT 'devcore',
                title TEXT NOT NULL,
                mode TEXT NOT NULL DEFAULT 'coding',
                status TEXT NOT NULL DEFAULT 'todo',
                steps_done INTEGER NOT NULL DEFAULT 0,
                steps_total INTEGER NOT NULL DEFAULT 1,
                depends_on TEXT,
                worktree TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                started_at TEXT,
                completed_at TEXT,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO tasks (id, project_id, title, status, mode, steps_total, steps_done, started_at, completed_at)
            SELECT id, COALESCE(project, 'devcore'), title, status, COALESCE(mode, 'coding'), COALESCE(steps_total, 1), COALESCE(steps_done, 0), started_at, completed_at
            FROM _legacy_tasks;
        """)
        cursor.execute("DROP TABLE _legacy_tasks;")

    # Align 'events' table
    table_info = cursor.execute("PRAGMA table_info(events);").fetchall()
    cols = {row[1]: row for row in table_info}
    if cols and ("project_id" not in cols or "created_at" not in cols):
        cursor.execute("ALTER TABLE events RENAME TO _legacy_events;")
        cursor.execute("""
            CREATE TABLE events (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL DEFAULT 'devcore',
                task_id TEXT,
                run_id TEXT,
                plugin_id TEXT,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                correlation_id TEXT,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        ts_col = "timestamp" if "timestamp" in cols else "created_at"
        proj_col = "project" if "project" in cols else "project_id"
        cursor.execute(f"""
            INSERT OR IGNORE INTO events (id, project_id, event_type, source, payload, created_at)
            SELECT id, COALESCE({proj_col}, 'devcore'), COALESCE(event_type, 'generic'), COALESCE(source, 'legacy'), COALESCE(payload, '{{}}'), COALESCE({ts_col}, datetime('now'))
            FROM _legacy_events;
        """)
        cursor.execute("DROP TABLE _legacy_events;")

    conn.commit()




def init_db(db_path: Optional[Path] = None) -> sqlite3.Connection:
    conn = connect_db(db_path)
    _align_existing_schema(conn)
    conn.executescript(INIT_SCHEMA_SQL)
    
    if HAS_SQLITE_VEC:
        try:
            conn.executescript(VECTOR_SCHEMA_SQL)
        except sqlite3.OperationalError as e:
            print(f"[WARN] Vector schema initialization note: {e}")
            
    conn.commit()
    return conn



if __name__ == "__main__":
    db_file = get_db_path()
    print(f"Initializing devcore.db at: {db_file}")
    connection = init_db(db_file)
    print(f"Database initialized successfully! sqlite-vec available: {HAS_SQLITE_VEC}")
    connection.close()
