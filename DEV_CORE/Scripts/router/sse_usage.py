"""Bounded observation of chat SSE; forwarding is owned by the caller."""
import asyncio
from .request_body import decode_json, BodyRefusal
from .usage import reported_usage


class SseUsage:
    LIMIT = 65536

    def __init__(self):
        self.line = bytearray()
        self.data = bytearray()
        self.usage = None
        self.done = self.disabled = False

    def _disable(self):
        self.disabled = True
        self.usage = None
        self.line.clear()
        self.data.clear()

    async def feed_async(self, chunk):
        """Observe a large transport chunk without monopolizing the event loop."""
        try:
            for start in range(0, len(chunk), self.LIMIT):
                if self.disabled or self.done:
                    return
                self.feed(chunk[start:start + self.LIMIT])
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            self._disable()
            raise

    def feed(self, chunk):
        if self.disabled or self.done:
            return
        start = 0
        while start < len(chunk):
            end = chunk.find(b'\n', start)
            stop = len(chunk) if end < 0 else end
            if len(self.line) + stop - start > self.LIMIT:
                self._disable()
                return
            self.line.extend(chunk[start:stop])
            if end < 0:
                return
            line = bytes(self.line).removesuffix(b'\r')
            self.line.clear()
            start = end + 1
            if not line:
                if self.data:
                    raw = bytes(self.data[:-1])
                    self.data.clear()
                    if raw == b'[DONE]':
                        self.done = True
                        return
                    try:
                        payload = decode_json(raw)
                        if isinstance(payload, dict) and payload.get('usage') is not None:
                            self.usage = reported_usage(payload)
                    except BodyRefusal:
                        self._disable()
                        return
            elif line == b'data' or line.startswith(b'data:'):
                value = line[5:] if line.startswith(b'data:') else b''
                if value.startswith(b' '):
                    value = value[1:]
                if len(self.data) + len(value) + 1 > self.LIMIT:
                    self._disable()
                    return
                self.data.extend(value)
                self.data.append(10)

    def result(self):
        return self.usage if self.done and not self.disabled else None
