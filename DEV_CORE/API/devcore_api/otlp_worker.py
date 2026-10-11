"""Single-loop, volatile, bounded export worker; no automatic retry."""
import asyncio
from collections import deque


class OtlpWorker:
    def __init__(self, exporter, *, max_events=256, max_bytes=1024 * 1024):
        if type(max_events) is not int or not 1 <= max_events <= 4096:
            raise ValueError('Invalid event capacity')
        if type(max_bytes) is not int or not 1024 <= max_bytes <= 16 * 1024 * 1024:
            raise ValueError('Invalid byte capacity')
        self.exporter = exporter  # Exclusive ownership, closed after drainage.
        self.max_events, self.max_bytes = max_events, max_bytes
        self._queue = deque()
        self._wake = asyncio.Event()
        self._loop = self._task = None
        self._pending = self._bytes = 0
        self.accepting = True
        self._counts = dict.fromkeys(('submitted', 'accepted', 'warnings', 'failed',
            'invalid', 'dropped', 'abandoned'), 0)

    def _count(self, key):
        self._counts[key] = min((1 << 63) - 1, self._counts[key] + 1)

    def _check_loop(self):
        if self._loop is not None and asyncio.get_running_loop() is not self._loop:
            raise RuntimeError('Worker belongs to another event loop')

    def start(self):
        self._check_loop()
        if not self.accepting or self.exporter.closed or self.exporter.busy:
            raise RuntimeError('Cannot start worker in current state')
        if self._task is None:
            self._loop = asyncio.get_running_loop()
            self._task = asyncio.create_task(self._run())

    def submit(self, event, *, start_ns, end_ns):
        self._check_loop()
        if not self.accepting:
            return 'closed'
        if self._task is None:
            return 'not_started'
        try:
            size = len(self.exporter.payload(event, start_ns, end_ns))
        except (ValueError, TypeError, OverflowError):
            self._count('invalid')
            return 'invalid'
        if self._pending >= self.max_events or self._bytes + size > self.max_bytes:
            self._count('dropped')
            return 'dropped'
        self._queue.append((event, start_ns, end_ns, size))
        self._pending += 1
        self._bytes += size
        self._count('submitted')
        self._wake.set()
        return 'queued'

    def snapshot(self):
        return {'scope': 'worker_instance', 'accepting': self.accepting,
            'running': self._task is not None and not self._task.done(),
            'pending': self._pending, 'queued': len(self._queue), 'pending_bytes': self._bytes,
            'max_events': self.max_events, 'max_bytes': self.max_bytes, **self._counts}

    async def _run(self):
        try:
            while self.accepting or self._queue:
                if not self._queue:
                    self._wake.clear()
                    await self._wake.wait()
                    continue
                event, start, end, size = self._queue.popleft()
                try:
                    try:
                        result = await self.exporter.export(event, start_ns=start, end_ns=end)
                    except Exception:
                        result = 'exception'  # Never retain error text.
                    if result == 'accepted':
                        self._count('accepted')
                    elif result == 'accepted_warning':
                        self._count('warnings')
                    else:
                        self._count('failed')
                except asyncio.CancelledError:
                    self._count('abandoned')
                    raise
                finally:
                    self._pending -= 1
                    self._bytes -= size
                await asyncio.sleep(0)
        finally:
            self.accepting = False
            while self._queue:
                _, _, _, size = self._queue.popleft()
                self._pending -= 1
                self._bytes -= size
                self._count('abandoned')
            closed = await self.exporter.aclose()
        return closed is True

    async def aclose(self, *, wait_seconds=2.0):
        self._check_loop()
        if type(wait_seconds) not in (int, float) or not 0 < wait_seconds <= 30:
            raise ValueError('Shutdown wait must be positive and at most 30 seconds')
        self.accepting = False
        self._wake.set()
        if self._task is None:
            return await self.exporter.aclose()
        try:
            return await asyncio.wait_for(asyncio.shield(self._task), wait_seconds)
        except TimeoutError:
            return False
