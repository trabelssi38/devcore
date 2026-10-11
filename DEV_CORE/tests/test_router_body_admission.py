"""Slow/cancelled inbound requests cannot monopolize auxiliary admission."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from starlette.requests import Request
from Scripts.router.request_body import read_json_body, decode_json, decode_json_async, BodyRefusal, SCAN_CHARS


def test_depth_bound_is_independent_of_python_parser_and_ignores_string_brackets():
    assert decode_json('[' * 64 + '0' + ']' * 64)
    with pytest.raises(BodyRefusal, match='excessive nesting'):
        decode_json('[' * 65 + '0' + ']' * 65)
    body = {'text': '[' * 100 + '"\\' + '}' * 100, 'model': 'gpt-4o'}
    assert decode_json(json.dumps(body)) == body


def test_async_scan_keeps_escape_state_across_boundaries_and_refuses_depth():
    async def scenario():
        raw = b'{"text":"' + b'a' * (SCAN_CHARS - 10) + b'\\"' + b'[' * 100 + b'"}'
        assert await decode_json_async(raw) == json.loads(raw)
        with pytest.raises(BodyRefusal):
            await decode_json_async('[' * 65 + '0' + ']' * 65)
    asyncio.run(scenario())


def test_scan_cancellation_stops_before_parse_completion():
    async def scenario():
        task = asyncio.create_task(decode_json_async(json.dumps({'text': 'x' * (2 * 1024 * 1024)})))
        await asyncio.sleep(0)
        assert not task.done()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(scenario())


def test_many_small_and_empty_chunks_preserve_body():
    async def scenario():
        remaining = 10000
        async def receive():
            nonlocal remaining
            remaining -= 1
            if remaining >= 0:
                return {'type': 'http.request', 'body': b' ' if remaining % 2 else b'', 'more_body': True}
            return {'type': 'http.request', 'body': b'{"text":"intact"}', 'more_body': False}
        assert await read_json_body(Request({'type': 'http'}, receive)) == {'text': 'intact'}
    asyncio.run(scenario())


def test_immediately_available_empty_chunks_cannot_bypass_deadline():
    async def scenario():
        events = 0
        async def receive():
            nonlocal events
            events += 1
            return {'type': 'http.request', 'body': b'' if events < 1000000 else b'{}', 'more_body': events < 1000000}
        with pytest.raises(BodyRefusal) as refusal:
            await read_json_body(Request({'type': 'http'}, receive), timeout=.02)
        assert refusal.value.status == 408 and events < 1000000
    asyncio.run(scenario())


def test_total_deadline_leaves_fast_request_available():
    async def scenario():
        entered, cancelled = asyncio.Event(), asyncio.Event()
        async def slow_receive():
            entered.set()
            try:
                await asyncio.sleep(.01)
                return {'type': 'http.request', 'body': b' ', 'more_body': True}
            except asyncio.CancelledError:
                cancelled.set()
                raise
        async def fast_receive():
            return {'type': 'http.request', 'body': b'{"model":"devcore-summary"}', 'more_body': False}
        slow = asyncio.create_task(read_json_body(Request({'type': 'http'}, slow_receive), timeout=.1))
        await entered.wait()
        assert await asyncio.wait_for(read_json_body(Request({'type': 'http'}, fast_receive)), .5) == {'model': 'devcore-summary'}
        assert not slow.done()
        with pytest.raises(BodyRefusal) as refusal:
            await asyncio.wait_for(slow, .5)
        assert refusal.value.status == 408 and cancelled.is_set()
    asyncio.run(scenario())


def test_chunked_body_limit_counts_total_not_last_chunk():
    async def scenario():
        events = iter([{'type': 'http.request', 'body': b'12345', 'more_body': True},
            {'type': 'http.request', 'body': b'6789', 'more_body': True}])
        async def receive():
            return next(events)
        with pytest.raises(BodyRefusal) as refusal:
            await read_json_body(Request({'type': 'http'}, receive), max_bytes=8)
        assert refusal.value.status == 413
    asyncio.run(scenario())


def test_external_cancellation_propagates():
    async def scenario():
        entered = asyncio.Event()
        async def receive():
            entered.set()
            await asyncio.Event().wait()
        task = asyncio.create_task(read_json_body(Request({'type': 'http'}, receive)))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(scenario())


def test_disconnect_refused_without_parsing_partial_body():
    async def scenario():
        async def receive():
            return {'type': 'http.disconnect'}
        with pytest.raises(BodyRefusal, match='disconnected'):
            await read_json_body(Request({'type': 'http'}, receive))
    asyncio.run(scenario())
