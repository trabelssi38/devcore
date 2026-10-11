"""Coalesce SSE refreshes per event loop, while preserving retry after failure."""
import asyncio
import math
from weakref import WeakKeyDictionary


class RefreshCoordinator:
    def __init__(self):
        self._states = WeakKeyDictionary()

    async def refresh(self, revision, producer):
        if type(revision) not in (int, float) or not math.isfinite(revision) or revision < 0:
            raise ValueError('Invalid dashboard refresh revision')
        loop = asyncio.get_running_loop()
        state = self._states.setdefault(loop, {'completed': None, 'task': None})
        while state['completed'] is None or revision > state['completed']:
            if state['task'] is None:
                async def run(target=revision):
                    try:
                        await asyncio.to_thread(producer)
                        state['completed'] = target
                    finally:
                        state['task'] = None
                task = loop.create_task(run())
                # A disconnected last subscriber must not leave an unobserved error.
                task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
                state['task'] = task
            await asyncio.shield(state['task'])
        return state['completed']
