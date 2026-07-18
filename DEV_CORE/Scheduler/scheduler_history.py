import sqlite3
import os
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import sys

# Add paths dynamically to resolve devcore.paths
scheduler_dir = Path(__file__).resolve().parent
platform_root = scheduler_dir.parent
tools_dir = platform_root / "Tools"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from devcore.paths import get_paths


def get_db_path() -> Path:
    """Get the path to the SQLite scheduler database."""
    paths = get_paths()
    db_dir = paths.data_root / "Scheduler"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "scheduler.db"


def init_db(db_path: Path) -> None:
    """Initialize the run_history table in the SQLite database."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    # Create run_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS run_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            scheduled_at TEXT NOT NULL,
            run_at TEXT NOT NULL,
            duration REAL NOT NULL,
            status TEXT NOT NULL,
            error TEXT,
            idempotency_key TEXT UNIQUE NOT NULL
        );
    """)
    # Add indexes for fast lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_run_history_job_scheduled 
        ON run_history (job_id, scheduled_at);
    """)
    conn.commit()
    conn.close()


def is_run_completed(job_id: str, scheduled_at: str, db_path: Optional[Path] = None) -> bool:
    """
    Check if a run for the given job_id and scheduled_at time is already completed or active.
    This checks the idempotency key in the run_history database.
    """
    if db_path is None:
        db_path = get_db_path()

    if not db_path.exists():
        return False

    idempotency_key = f"{job_id}:{scheduled_at}"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM run_history WHERE idempotency_key = ? AND status IN ('ok', 'skipped', 'running')",
        (idempotency_key,)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None


def record_run(
    job_id: str,
    scheduled_at: str,
    run_at: str,
    duration: float,
    status: str,
    error: Optional[str] = None,
    db_path: Optional[Path] = None
) -> bool:
    """
    Record a job execution run in the SQLite run history.
    Returns True if successfully recorded, or False if blocked by the idempotency key unique constraint.
    """
    if db_path is None:
        db_path = get_db_path()

    init_db(db_path)

    idempotency_key = f"{job_id}:{scheduled_at}"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO run_history (job_id, scheduled_at, run_at, duration, status, error, idempotency_key)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, scheduled_at, run_at, duration, status, error, idempotency_key)
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        # Unique constraint violation - idempotency blocked the run
        conn.rollback()
        success = False
    finally:
        conn.close()

    return success


def update_run(
    job_id: str,
    scheduled_at: str,
    duration: float,
    status: str,
    error: Optional[str] = None,
    db_path: Optional[Path] = None
) -> bool:
    """Update an existing job execution run record in the SQLite run history."""
    if db_path is None:
        db_path = get_db_path()

    idempotency_key = f"{job_id}:{scheduled_at}"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE run_history
            SET duration = ?, status = ?, error = ?, run_at = ?
            WHERE idempotency_key = ?
            """,
            (duration, status, error, datetime.now().isoformat(), idempotency_key)
        )
        conn.commit()
        success = True
    except Exception:
        conn.rollback()
        success = False
    finally:
        conn.close()
    return success
