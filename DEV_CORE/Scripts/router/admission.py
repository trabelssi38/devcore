"""Per-ASGI-instance capacity; no waiting queue or automatic retry."""
import asyncio
import json

COUNTER_MAX = (1 << 63) - 1


class AdmissionGuard:
    def __init__(self, app, *, max_requests=8):
        if type(max_requests) is not int or not 1 <= max_requests <= 64:
            raise ValueError('Admission capacity must be between 1 and 64')
        self.app = app
        self.capacity = max_requests
        self.slots = asyncio.Semaphore(max_requests)
        self.active = self.peak = 0
        self.counters = dict.fromkeys(('admitted', 'finished', 'exceptions', 'cancelled',
            'rejected_http', 'rejected_websocket'), 0)
        self.saturated = False

    def count(self, key):
        if self.counters[key] < COUNTER_MAX:
            self.counters[key] += 1
        else:
            self.saturated = True

    def snapshot(self):
        return {'schema_version': 1, 'scope': 'asgi_instance', 'capacity': self.capacity,
            'active': self.active, 'peak_active': self.peak,
            'counters_saturated': self.saturated, **self.counters}

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and scope['method'] == 'GET' and scope.get('path') == '/devcore/admission':
            body = json.dumps(self.snapshot()).encode()
            await send({'type': 'http.response.start', 'status': 200,
                'headers': [(b'content-type', b'application/json'), (b'cache-control', b'no-store')]})
            return await send({'type': 'http.response.body', 'body': body})
        limited = scope['type'] == 'websocket' or (
            scope['type'] == 'http' and scope['method'] == 'POST')
        if not limited:
            return await self.app(scope, receive, send)
        # On one ASGI event loop, acquire() doesn't yield when capacity is
        # available; checking locked() first avoids adding a waiting request.
        if self.slots.locked():
            if scope['type'] == 'websocket':
                self.count('rejected_websocket')
                return await send({'type': 'websocket.close', 'code': 1013})
            self.count('rejected_http')
            body = json.dumps({'error': {'type': 'service_capacity_exceeded',
                'message': 'Service capacity reached'}}).encode()
            await send({'type': 'http.response.start', 'status': 503,
                'headers': [(b'content-type', b'application/json'), (b'retry-after', b'1')]})
            return await send({'type': 'http.response.body', 'body': body})
        await self.slots.acquire()
        self.active += 1
        self.peak = max(self.peak, self.active)
        self.count('admitted')
        try:
            # Keep capacity through streaming and deferred ASGI cleanup.
            result = await self.app(scope, receive, send)
        except asyncio.CancelledError:
            self.count('cancelled')
            raise
        except BaseException:
            self.count('exceptions')
            raise
        else:
            self.count('finished')
            return result
        finally:
            self.active -= 1
            self.slots.release()
