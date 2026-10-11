"""Immediate admission and lifetime accounting for legacy dashboard SSE."""
import asyncio
from weakref import WeakKeyDictionary, finalize

from starlette.responses import StreamingResponse


class StreamCapacityExceeded(RuntimeError):
    pass


class StreamSlots:
    def __init__(self, limit=32):
        if type(limit) is not int or limit < 1:
            raise ValueError('Invalid SSE connection limit')
        self.limit = limit
        self._states = WeakKeyDictionary()

    def reserve(self):
        state = self._states.setdefault(asyncio.get_running_loop(), {'active': 0})
        if state['active'] >= self.limit:
            raise StreamCapacityExceeded('SSE connection capacity reached')
        state['active'] += 1
        released = False
        def release():
            nonlocal released
            if not released:
                state['active'] -= 1
                released = True
        return release


class AdmittedStreamingResponse(StreamingResponse):
    def __init__(self, content, slots, **kwargs):
        super().__init__(content, **kwargs)
        self._release = slots.reserve()
        # A middleware can abandon the response before ASGI dispatch.
        # The callback owns only the slot state, never the response itself.
        self._finalizer = finalize(self, self._release)

    async def __call__(self, scope, receive, send):
        try:
            return await super().__call__(scope, receive, send)
        finally:
            try:
                close = getattr(self.body_iterator, 'aclose', None)
                if close is not None:
                    await close()
            finally:
                self._finalizer()
