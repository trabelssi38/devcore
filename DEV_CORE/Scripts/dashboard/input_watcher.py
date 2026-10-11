"""Shared bounded-rate input probes for legacy global dashboard SSE."""
import asyncio
import math
from weakref import WeakKeyDictionary


class ProbeCooldownError(RuntimeError):
    """A previous failed probe is still inside its retry interval."""


class ProbeTimeoutError(TimeoutError):
    """The caller stopped waiting; the one shared OS probe may still run."""


class InputWatcher:
    def __init__(self, interval=1.0, timeout=5.0):
        if type(interval) not in (int, float) or not math.isfinite(interval) or interval < 0:
            raise ValueError('Invalid dashboard watcher interval')
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('Invalid dashboard watcher timeout')
        self.interval = interval
        self.timeout = timeout
        self._states = WeakKeyDictionary()

    async def revision(self, probe):
        return (await self._sample(probe))['revision']

    async def snapshot(self, probe):
        """Return revision and value from the same sample, including None."""
        state = await self._sample(probe)
        return state['revision'], state['signature']

    async def _sample(self, probe):
        loop = asyncio.get_running_loop()
        state = self._states.setdefault(loop, {
            'initialized': False, 'signature': None, 'revision': 0,
            'sampled_at': None, 'task': None,
            'failed_at': None, 'failure_message': None,
        })
        if (state['task'] is None and state['failed_at'] is not None
                and loop.time() - state['failed_at'] < self.interval):
            # Store bounded text, not an exception whose traceback grows on reuse.
            raise ProbeCooldownError(state['failure_message'])
        if state['task'] is None and (state['sampled_at'] is None
                or loop.time() - state['sampled_at'] >= self.interval):
            async def sample():
                try:
                    signature = await asyncio.to_thread(probe)
                    if not state['initialized'] or signature != state['signature']:
                        state['revision'] += 1
                        state['signature'] = signature
                        state['initialized'] = True
                    state['sampled_at'] = loop.time()
                    state['failed_at'] = None
                    state['failure_message'] = None
                except Exception as error:
                    state['failed_at'] = loop.time()
                    state['failure_message'] = str(error)[:1024]
                    raise
                finally:
                    state['task'] = None
            task = loop.create_task(sample())
            task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
            state['task'] = task
        if state['task'] is not None:
            deadline = asyncio.timeout(self.timeout)
            try:
                async with deadline:
                    await asyncio.shield(state['task'])
            except TimeoutError:
                if deadline.expired():
                    raise ProbeTimeoutError('Dashboard probe wait deadline exceeded') from None
                raise  # Preserve an actual TimeoutError raised by the probe.
        return state
