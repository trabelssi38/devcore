"""Bound repeated SSE diagnostics per event loop, not per subscriber."""
import asyncio
import math
from weakref import WeakKeyDictionary


class SseErrorReporter:
    PHASES = ('cache', 'loop')

    def __init__(self, interval=30.0, emit=None):
        if type(interval) not in (int, float) or not math.isfinite(interval) or interval <= 0:
            raise ValueError('Invalid SSE diagnostic interval')
        self.interval = interval
        self.emit = print if emit is None else emit
        self._states = WeakKeyDictionary()

    def report(self, phase, error):
        if phase not in self.PHASES:
            raise ValueError('Invalid SSE diagnostic phase')
        loop = asyncio.get_running_loop()
        states = self._states.setdefault(loop, {})
        state = states.setdefault(phase, {'reported_at': None, 'suppressed': 0})
        now = loop.time()
        if state['reported_at'] is not None and now - state['reported_at'] < self.interval:
            state['suppressed'] = min(state['suppressed'] + 1, 999999)
            return False
        suppressed = state['suppressed']
        state.update(reported_at=now, suppressed=0)
        try:
            detail = str(error)[:1024].replace('\r', '\\r').replace('\n', '\\n')
            self.emit(f'[DashboardAPI-SSE] {phase}: {detail}; suppressed={suppressed}')
        except Exception:
            # A failing output sink must not replace the stream's recovery path.
            return False
        return True
