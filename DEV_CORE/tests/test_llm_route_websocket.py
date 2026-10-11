"""Frame admission is checked on every native Responses message, without network."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from Scripts.headroom_routes import RouteGuard


def run_frames(frames, *, route="native", path="/v1/responses", headers=None):
    observed, output = [], []
    async def scenario():
        events = iter([{"type": "websocket.connect"}] + frames + [{"type": "websocket.disconnect", "code": 1000}])
        async def receive():
            return next(events)
        async def send(event):
            output.append(event)
        async def app(scope, receive, send):
            assert (await receive())["type"] == "websocket.connect"
            await send({"type": "websocket.accept"})
            while True:
                event = await receive()
                if event["type"] == "websocket.disconnect":
                    return
                observed.append(event)
        await RouteGuard(app, route)({"type": "websocket", "path": path, "headers": headers or []}, receive, send)
    asyncio.run(scenario())
    return observed, output


def frame(body):
    return {"type": "websocket.receive", "text": json.dumps(body)}


@pytest.mark.parametrize("wrapped", [False, True])
def test_native_frames_preserved_verbatim(wrapped):
    body = {"model": "gpt-6-codex", "input": [{"role": "user", "content": "hello"}]}
    message = {"type": "response.create", "response": body} if wrapped else {"type": "response.create", **body}
    event = frame(message)
    observed, output = run_frames([event, event])
    assert observed == [event, event]
    assert output == [{"type": "websocket.accept"}]


@pytest.mark.parametrize("body", [
    {"type": "response.create", "model": "devcore-bulk"},
    {"type": "response.create", "model": "claude-test"},
    {"type": "response.create", "model": "gemini-2.5-flash"},
    {"type": "response.create", "model": "gpt-4o", "provider": "gemini"},
    {"type": "response.create", "model": "gpt-4o", "fallback_providers": []},
    {"type": "response.create", "response": {"model": "gpt-4o"}, "base_url": "http://127.0.0.1:20130"},
    {"type": "response.create", "response": {"model": "gpt-4o", "upstream_model": "gemini-test"}},
    {"type": "response.create"},
    {"type": "response.create", "response": []},
    {"type": "session.update", "model": "gpt-4o"},
])
def test_invalid_later_frame_is_not_forwarded(body):
    valid = frame({"type": "response.create", "model": "gpt-4o"})
    observed, output = run_frames([valid, frame(body), valid])
    assert observed == [valid]
    assert output[-1] == {"type": "websocket.close", "code": 1008}


@pytest.mark.parametrize("event", [
    {"type": "websocket.receive", "bytes": b"binary"},
    {"type": "websocket.receive", "text": "invalid JSON"},
    {"type": "websocket.receive", "text": '[' * 1500 + ']' * 1500},
    frame([]),
])
def test_malformed_frame_refused(event):
    observed, output = run_frames([event])
    assert observed == [] and output[-1]["code"] == 1008


@pytest.mark.parametrize("route,path,headers", [
    ("auxiliary", "/v1/responses", []),
    ("native", "/v1/messages", []),
    ("native", "/v1/responses", [(b"x-headroom-base-url", b"http://127.0.0.1:20130")]),
])
def test_unapproved_handshake_rejected(route, path, headers):
    observed, output = run_frames([], route=route, path=path, headers=headers)
    assert observed == [] and output == [{"type": "websocket.close", "code": 1008}]
