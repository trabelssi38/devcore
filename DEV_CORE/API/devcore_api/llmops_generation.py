"""Explicit observation of successful async generations; no routing or retry.

The application supplies a bounded synchronous event factory from the actual
result. No prompt, token estimate, cost default or error text is collected.
The worker must already be started on this loop and drained by its owner.
"""
import time


class GenerationObserver:
    def __init__(self, worker, *, clock=time.time_ns):
        self.worker = worker
        self.clock = clock
        self._counts = dict.fromkeys(('queued', 'refused', 'invalid', 'errors'), 0)

    def _count(self, key):
        self._counts[key] = min((1 << 63) - 1, self._counts[key] + 1)

    def snapshot(self):
        return {'scope': 'observer_instance', **self._counts}

    async def run(self, operation, *, event_from_result):
        # Ordinary telemetry errors must not alter the operation's outcome.
        try:
            start = self.clock()
        except Exception:
            start = None
        result = await operation()
        try:
            end = self.clock()
            if start is None:
                self._count('errors')
                return result
            event = event_from_result(result)
            status = self.worker.submit(event, start_ns=start, end_ns=end)
            if status == 'queued':
                self._count('queued')
            elif status == 'invalid':
                self._count('invalid')
            else:
                self._count('refused')
        except Exception:
            self._count('errors')
        return result
