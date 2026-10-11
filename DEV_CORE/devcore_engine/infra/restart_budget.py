"""Local restart reservations shared by watchdog instances and processes."""
from contextlib import closing
from pathlib import Path
import sqlite3
import time
import uuid
import math


class RestartBudget:
    WINDOW = 600.0
    LIMIT = 3
    LEASE = 60.0

    def __init__(self, path: Path):
        self.path = Path(path)

    def reserve(self, service: str, *, now=None):
        now = time.time() if now is None else now
        if not isinstance(service, str) or not service or len(service) > 256:
            raise ValueError("Invalid service key")
        if type(now) not in (int, float) or not math.isfinite(now) or now < 0:
            raise ValueError("Invalid reservation time")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=0.2)) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS restart_budget (service TEXT PRIMARY KEY, owner TEXT NOT NULL, attempts INTEGER NOT NULL, window_start REAL NOT NULL, next_attempt REAL NOT NULL, lease_until REAL NOT NULL)")
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT attempts, window_start, next_attempt, lease_until FROM restart_budget WHERE service=?", (service,)).fetchone()
            if row and not self._valid_state(row):
                conn.rollback()
                return None, "restart_state_invalid"
            attempts, start, next_attempt, lease_until = row or (0, now, now, 0)
            if lease_until > now:
                conn.rollback()
                return None, "restart_in_progress"
            if now - start >= self.WINDOW:
                attempts, start, next_attempt = 0, now, now
            if attempts >= self.LIMIT:
                conn.rollback()
                return None, "restart_budget_exhausted"
            if next_attempt > now:
                conn.rollback()
                return None, "restart_backoff"
            owner = uuid.uuid4().hex
            cooldown = 5.0 * (2 ** attempts)
            conn.execute("INSERT OR REPLACE INTO restart_budget VALUES (?,?,?,?,?,?)",
                (service, owner, attempts + 1, start, now + cooldown, now + self.LEASE))
            conn.commit()
            return owner, "restart_reserved"

    @classmethod
    def _valid_state(cls, row):
        attempts, start, next_attempt, lease_until = row
        return (type(attempts) is int and 1 <= attempts <= cls.LIMIT
            and all(type(value) in (int, float) and math.isfinite(value) and value >= 0
                    for value in (start, next_attempt, lease_until))
            and next_attempt >= start
            and (lease_until == 0 or lease_until >= start))

    def release(self, service: str, owner: str):
        with closing(sqlite3.connect(self.path, timeout=0.2)) as conn:
            conn.execute("UPDATE restart_budget SET lease_until=0 WHERE service=? AND owner=?", (service, owner))
            conn.commit()
