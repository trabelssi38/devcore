"""ASGI liveness checks without services, credentials, active data or network."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from Scripts.headroom_routes import RouteGuard


def scope(path="/v1/responses"):
    return {"type": "http", "path": path, "method": "POST", "headers": []}


def test_slow_body_does_not_block_other_request_and_deadline_is_total():
    async def scenario():
        calls, slow_output, fast_output = [], [], []
        first_chunk = asyncio.Event()
        cancelled = asyncio.Event()
        async def app(scope, receive, send):
            event = await receive()
            calls.append(json.loads(event["body"])["model"])
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})
        guard = RouteGuard(app, "native", body_timeout=0.1)
        async def slow_receive():
            first_chunk.set()
            try:
                await asyncio.sleep(0.01)
                return {"type": "http.request", "body": b" ", "more_body": True}
            except asyncio.CancelledError:
                cancelled.set()
                raise
        async def slow_send(event):
            slow_output.append(event)
        async def fast_send(event):
            fast_output.append(event)
        async def fast_receive():
            return {"type": "http.request", "body": b'{"model":"gpt-4o"}', "more_body": False}
        slow = asyncio.create_task(guard(scope(), slow_receive, slow_send))
        await first_chunk.wait()
        await asyncio.wait_for(guard(scope(), fast_receive, fast_send), 0.5)
        assert not slow.done()
        assert fast_output[0]["status"] == 200
        await asyncio.wait_for(slow, 0.5)
        assert slow_output[0]["status"] == 408
        assert cancelled.is_set()
        assert calls == ["gpt-4o"]
        assert len(guard.events) == 1
    asyncio.run(scenario())


def test_stream_chunks_are_forwarded_without_buffering_response():
    async def scenario():
        output = []
        first_sent = asyncio.Event()
        release = asyncio.Event()
        async def app(scope, receive, send):
            event = await receive()
            assert json.loads(event["body"])["model"] == "claude-test"
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"first", "more_body": True})
            await release.wait()
            await send({"type": "http.response.body", "body": b"last", "more_body": False})
        guard = RouteGuard(app, "native")
        async def receive():
            return {"type": "http.request", "body": b'{"model":"claude-test","stream":true}', "more_body": False}
        async def send(event):
            output.append(event)
            if event.get("body") == b"first":
                first_sent.set()
        task = asyncio.create_task(guard(scope("/v1/messages"), receive, send))
        await asyncio.wait_for(first_sent.wait(), 0.5)
        assert not task.done() and output[-1]["body"] == b"first"
        release.set()
        await asyncio.wait_for(task, 0.5)
        assert [e["body"] for e in output if e["type"] == "http.response.body"] == [b"first", b"last"]
    asyncio.run(scenario())


@pytest.mark.parametrize("event", [
    {"type": "http.disconnect"},
    {"type": "http.request", "body": b"x" * (16 * 1024 * 1024 + 1), "more_body": False},
])
def test_disconnected_or_oversized_body_never_reaches_upstream(event):
    async def scenario():
        output = []
        async def app(*args):
            pytest.fail("Invalid body must not reach upstream")
        async def receive():
            return event
        async def send(message):
            output.append(message)
        await RouteGuard(app, "native")(scope(), receive, send)
        if event["type"] == "http.disconnect":
            assert output == []
        else:
            assert output[0]["status"] == 413
    asyncio.run(scenario())


def test_external_cancellation_is_not_converted_to_response():
    async def scenario():
        reading = asyncio.Event()
        async def app(*args):
            pytest.fail("Cancelled body must not reach upstream")
        async def receive():
            reading.set()
            await asyncio.Event().wait()
        async def send(message):
            pytest.fail("External cancellation must propagate")
        task = asyncio.create_task(RouteGuard(app, "native")(scope(), receive, send))
        await reading.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(scenario())


@pytest.mark.parametrize('route,model', [('native', 'gpt-4o'), ('auxiliary', 'devcore-summary')])
def test_large_json_scan_leaves_health_available_before_upstream(route, model):
    async def scenario():
        received = asyncio.Event()
        calls, health_output = [], []
        body = json.dumps({'model': model, 'input': 'x' * (2 * 1024 * 1024)}).encode()
        async def app(scope, receive, send):
            event = await receive()
            calls.append(event['body'])
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'ok'})
        async def receive():
            received.set()
            return {'type': 'http.request', 'body': body, 'more_body': False}
        async def discard(event):
            pass
        async def capture(event):
            health_output.append(event)
        guard = RouteGuard(app, route)
        path = '/v1/responses' if route == 'native' else '/v1/chat/completions'
        request = asyncio.create_task(guard(scope(path), receive, discard))
        try:
            await received.wait()
            await guard({'type': 'http', 'path': '/healthz', 'method': 'GET', 'headers': []}, receive, capture)
            assert not request.done() and calls == []
            assert json.loads(health_output[-1]['body'])['service'] == 'headroom-devcore'
            await asyncio.wait_for(request, 3)
            assert calls == [body]
        finally:
            if not request.done():
                request.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await request
    asyncio.run(scenario())


def test_immediate_empty_chunk_flood_obeys_headroom_deadline():
    async def scenario():
        events, output = 0, []
        async def receive():
            nonlocal events
            events += 1
            return {'type': 'http.request', 'body': b'' if events < 1000000 else b'{"model":"gpt-4o"}', 'more_body': events < 1000000}
        async def app(*args):
            pytest.fail('Empty chunk flood reached upstream')
        async def send(event):
            output.append(event)
        await RouteGuard(app, 'native', body_timeout=.02)(scope(), receive, send)
        assert output[0]['status'] == 408 and events < 1000000
    asyncio.run(scenario())


@pytest.mark.parametrize("ready,expected", [(False, 503), (True, 200)])
def test_health_waits_for_headroom_startup(ready, expected):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.state.ready = ready
    with TestClient(RouteGuard(app, "native")) as client:
        response = client.get("/healthz")
        assert response.status_code == expected
        assert response.json()["status"] == ("ready" if ready else "not_ready")
