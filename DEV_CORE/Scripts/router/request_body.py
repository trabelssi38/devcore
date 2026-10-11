"""Bounded JSON admission before routing, state access or provider calls."""
import asyncio
import json

from starlette.requests import ClientDisconnect

MAX_BODY_BYTES = 16 * 1024 * 1024
MAX_JSON_DEPTH = 64
SCAN_CHARS = 64 * 1024
STREAM_YIELD_EVERY = 64


class BodyRefusal(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def depth_steps(text):
    depth, quoted, escaped = 0, False, False
    for start in range(0, len(text), SCAN_CHARS):
        for char in text[start:start + SCAN_CHARS]:
            if quoted:
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in '[{':
                depth += 1
                if depth > MAX_JSON_DEPTH:
                    raise ValueError('Excessive nesting')
            elif char in ']}':
                depth -= 1
        yield


def decode_json(raw):
    try:
        text = raw.decode('utf-8') if isinstance(raw, (bytes, bytearray)) else raw
        for _ in depth_steps(text):
            pass
        return json.loads(text)
    except (ValueError, RecursionError) as exc:
        # Never expose parser internals or attacker-controlled payload text.
        raise BodyRefusal('Invalid JSON or excessive nesting') from exc


async def decode_json_async(raw):
    try:
        text = raw.decode('utf-8') if isinstance(raw, (bytes, bytearray)) else raw
        for _ in depth_steps(text):
            # No orphan worker: cancellation stops this request's scan.
            await asyncio.sleep(0)
        # The standard JSON parse and UTF-8 decoding remain synchronous.
        return json.loads(text)
    except (ValueError, RecursionError) as exc:
        raise BodyRefusal('Invalid JSON or excessive nesting') from exc


async def read_json_body(request, *, timeout=30.0, max_bytes=MAX_BODY_BYTES):
    if type(timeout) not in (int, float) or not 0 < timeout <= 30:
        raise ValueError('Body timeout must be positive and at most 30 seconds')
    if type(max_bytes) is not int or not 0 < max_bytes <= MAX_BODY_BYTES:
        raise ValueError('Invalid body byte limit')
    buffer = bytearray()
    events = 0
    try:
        async with asyncio.timeout(timeout):
            # Request.stream() hides empty events, which could starve the
            # deadline before yielding a chunk. Observe each ASGI event.
            while True:
                event = await request.receive()
                if event['type'] == 'http.disconnect':
                    raise ClientDisconnect()
                if event['type'] != 'http.request':
                    raise BodyRefusal('Invalid request body event')
                chunk = event.get('body', b'')
                if len(buffer) + len(chunk) > max_bytes:
                    raise BodyRefusal('Request exceeds body byte limit', 413)
                buffer.extend(chunk)
                events += 1
                if events % STREAM_YIELD_EVERY == 0:
                    await asyncio.sleep(0)
                if not event.get('more_body', False):
                    break
    except TimeoutError as exc:
        raise BodyRefusal('Request body deadline exceeded', 408) from exc
    except ClientDisconnect as exc:
        raise BodyRefusal('Client disconnected before body completion') from exc
    return await decode_json_async(buffer)
