"""Local generation lock held by the OS, never stolen based on file age."""
import errno
import os
from pathlib import Path
import time


class DashboardLock:
    """Persistent file, exclusive kernel lock; all local writers must cooperate."""
    LOCK_FILENAME = "gen_dashboard.lock"
    WAIT_TIMEOUT = 30

    def __init__(self, wait_timeout=None):
        root = os.environ.get("DEVCORE_LOCAL_ROOT")
        if not root:
            root = (str(Path(os.getenv("LOCALAPPDATA")) / "DEV_CORE_LOCAL")
                    if os.name == "nt" and os.getenv("LOCALAPPDATA")
                    else os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[3] / "DEV_CORE_DATA")))
        self.lock_path = Path(root) / "Runtime" / self.LOCK_FILENAME
        self.wait_timeout = self.WAIT_TIMEOUT if wait_timeout is None else wait_timeout
        self._stream = None

    def _acquire(self, stream):
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def __enter__(self):
        if self._stream is not None:
            raise RuntimeError("Dashboard lock already held by this object")
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.lock_path.open("a+b")
        try:
            if os.fstat(stream.fileno()).st_size == 0:
                stream.write(b"0")
                stream.flush()
            deadline = time.monotonic() + self.wait_timeout
            while True:
                try:
                    self._acquire(stream)
                    self._stream = stream
                    return self
                except OSError as error:
                    if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                        raise
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Dashboard generation already in progress") from error
                    time.sleep(min(0.1, max(0, deadline - time.monotonic())))
        except BaseException:
            stream.close()
            raise

    def __exit__(self, *_):
        stream, self._stream = self._stream, None
        if stream is None:
            return
        try:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()
        # Never unlink: contenders must retain the same file/inode.
