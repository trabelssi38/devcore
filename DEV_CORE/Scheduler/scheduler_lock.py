"""Local scheduler lease: serialized read/modify/write, never shared via sync."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import errno


class SchedulerGuardBusy(OSError):
    """The opened guard's nonblocking OS lock is held by another participant."""


class SchedulerLeaseLock:
    def __init__(self, lock_path: Path, owner_id: str, lease_duration_seconds: int = 30):
        if not isinstance(owner_id, str) or not owner_id or len(owner_id) > 256:
            raise ValueError('Invalid scheduler owner')
        if type(lease_duration_seconds) is not int or not 1 <= lease_duration_seconds <= 3600:
            raise ValueError('Invalid scheduler lease duration')
        self.lock_path = Path(lock_path)
        self.owner_id = owner_id
        self.lease_duration_seconds = lease_duration_seconds

    @contextmanager
    def _guard(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        # This persistent guard must never be replaced or unlinked by writers.
        with open(self.lock_path.with_suffix(self.lock_path.suffix + '.guard'), 'a+b') as guard:
            guard.seek(0, os.SEEK_END)
            if guard.tell() == 0:
                guard.write(b'0')
                guard.flush()
            guard.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(guard.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(guard.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise SchedulerGuardBusy('Scheduler guard busy') from exc
                raise
            try:
                yield
            finally:
                guard.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(guard.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(guard.fileno(), fcntl.LOCK_UN)

    def _read_lock(self):
        try:
            with open(self.lock_path, 'rb') as stream:
                raw = stream.read(65537)
        except FileNotFoundError:
            return None
        if len(raw) > 65536:
            raise ValueError('Oversized scheduler lease')
        data = json.loads(raw)
        if not isinstance(data, dict) or not isinstance(data.get('owner'), str) or not data['owner'] or len(data['owner']) > 256:
            raise ValueError('Invalid scheduler lease')
        expiry = datetime.fromisoformat(data['expires_at'])
        return data, expiry

    @staticmethod
    def _active(expiry):
        # Existing naive timestamps remain local time; new timestamps use UTC.
        return expiry > datetime.now(expiry.tzinfo)

    def _write_lock(self):
        payload = {'owner': self.owner_id, 'expires_at':
            (datetime.now(timezone.utc) + timedelta(seconds=self.lease_duration_seconds)).isoformat()}
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.lock_path.parent,
                    prefix=self.lock_path.name + '.', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(payload, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.lock_path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def get_owner(self):
        try:
            with self._guard():
                row = self._read_lock()
                return row[0]['owner'] if row and self._active(row[1]) else None
        except (OSError, ValueError, TypeError, KeyError):
            return None

    def is_active(self):
        return self.get_owner() is not None

    def acquire(self):
        try:
            with self._guard():
                row = self._read_lock()
                if row and self._active(row[1]) and row[0]['owner'] != self.owner_id:
                    return False
                self._write_lock()
                return True
        except (OSError, ValueError, TypeError, KeyError):
            return False

    @contextmanager
    def hold(self):
        """Keep the OS guard throughout work, even if the timed lease expires.

        Callers must not invoke lease methods recursively inside this scope.
        All participating schedulers must use this protocol before activation.
        """
        with self._guard():
            row = self._read_lock()
            if not row or row[0]['owner'] != self.owner_id or not self._active(row[1]):
                raise RuntimeError('Scheduler lease unavailable before execution')
            yield
            self._write_lock()

    @contextmanager
    def registry_guard(self):
        """Serialize registry updates with executing scheduler cycles."""
        with self._guard():
            self._read_lock()  # Invalid lease is never silently bypassed.
            yield

    @contextmanager
    def maintenance_guard(self):
        """Exclude participating cycles and refuse an unexpired scheduler lease."""
        with self._guard():
            row = self._read_lock()
            if row and self._active(row[1]):
                raise RuntimeError('Stop the scheduler and wait for its lease before maintenance')
            yield

    def renew(self):
        try:
            with self._guard():
                row = self._read_lock()
                if not row or row[0]['owner'] != self.owner_id or not self._active(row[1]):
                    return False
                self._write_lock()
                return True
        except (OSError, ValueError, TypeError, KeyError):
            return False

    def release(self):
        try:
            with self._guard():
                row = self._read_lock()
                if not row or row[0]['owner'] != self.owner_id:
                    return False
                self.lock_path.unlink()
                return True
        except (OSError, ValueError, TypeError, KeyError):
            return False
