import json
import os
import time
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class SchedulerLeaseLock:
    def __init__(self, lock_path: Path, owner_id: str, lease_duration_seconds: int = 30):
        self.lock_path = lock_path
        self.owner_id = owner_id
        self.lease_duration_seconds = lease_duration_seconds

    def _read_lock(self) -> Optional[Dict[str, Any]]:
        """Read the lock file and return its parsed contents if valid."""
        if not self.lock_path.exists():
            return None
        try:
            with open(self.lock_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Validate schema
            if "owner" in data and "expires_at" in data:
                return data
        except Exception:
            # Corrupted lock file behaves as expired/deleted
            pass
        return None

    def _write_lock(self, expires_at: datetime) -> None:
        """Write owner and expiration info to the lock file."""
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "owner": self.owner_id,
            "expires_at": expires_at.isoformat()
        }
        # Atomic file write to avoid partial writes
        temp_path = self.lock_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        
        # Windows-safe rename fallback
        if self.lock_path.exists():
            try:
                os.remove(self.lock_path)
            except Exception:
                pass
        os.rename(temp_path, self.lock_path)

    def is_active(self) -> bool:
        """Check if the lock is currently held by an active owner."""
        lock = self._read_lock()
        if not lock:
            return False
        try:
            expires_at = datetime.fromisoformat(lock["expires_at"])
            return expires_at > datetime.now()
        except Exception:
            return False

    def get_owner(self) -> Optional[str]:
        """Get the ID of the current active owner, or None if expired/free."""
        lock = self._read_lock()
        if not lock:
            return None
        try:
            expires_at = datetime.fromisoformat(lock["expires_at"])
            if expires_at > datetime.now():
                return lock["owner"]
        except Exception:
            pass
        return None

    def acquire(self) -> bool:
        """
        Attempt to acquire the lease lock.
        Returns True if acquired, False otherwise.
        """
        lock = self._read_lock()
        now = datetime.now()

        if lock:
            try:
                expires_at = datetime.fromisoformat(lock["expires_at"])
                if expires_at > now:
                    # Lock is held by another active instance
                    if lock["owner"] == self.owner_id:
                        # We already own it, renew it
                        return self.renew()
                    return False
            except Exception:
                pass

        # Write lock file
        expires_at = now + timedelta(seconds=self.lease_duration_seconds)
        try:
            self._write_lock(expires_at)
        except Exception:
            return False

        # Sleep a small randomized jitter to resolve collision race conditions
        time.sleep(random.uniform(0.05, 0.15))

        # Verify that we succeeded and still hold the lock
        lock_verify = self._read_lock()
        if lock_verify and lock_verify["owner"] == self.owner_id:
            return True
        return False

    def renew(self) -> bool:
        """
        Renew the lease lock if we are the current owner.
        Returns True if renewed, False otherwise.
        """
        lock = self._read_lock()
        if not lock or lock["owner"] != self.owner_id:
            return False
        
        now = datetime.now()
        expires_at = now + timedelta(seconds=self.lease_duration_seconds)
        try:
            self._write_lock(expires_at)
            return True
        except Exception:
            return False

    def release(self) -> bool:
        """
        Release the lease lock. Only succeeds if we own it.
        Returns True if released, False otherwise.
        """
        lock = self._read_lock()
        if not lock or lock["owner"] != self.owner_id:
            return False

        try:
            if self.lock_path.exists():
                os.remove(self.lock_path)
            return True
        except Exception:
            return False
