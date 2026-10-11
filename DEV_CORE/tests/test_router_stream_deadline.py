"""Absolute stream budget closes upstream without cancelling consumer sends."""
import asyncio
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from router import stream_parser


@pytest.mark.parametrize('mode', ['before', 'after', 'backoff', 'consumer_pause', 'cancel'])
def test_deadline_closes_upstream_and_preserves_external_cancellation(monkeypatch, mode):
    async def scenario():
        opened, closed, recorded = [], [], []
        entered = asyncio.Event()
        raw = b'data: {"choices":[]}\n\n'
        class Response:
            headers = {}
            status_code = 500 if mode == 'backoff' else 200
            def raise_for_status(self):
                pass
            async def aiter_raw(self):
                entered.set()
                if mode in ('after', 'consumer_pause'):
                    yield raw
                await asyncio.Event().wait()
        class Context:
            async def __aenter__(self):
                opened.append(1)
                entered.set()
                return Response()
            async def __aexit__(self, *args):
                closed.append(1)
        class Client:
            def stream(self, *args, **kwargs):
                return Context()
        monkeypatch.setattr(stream_parser, 'client', Client())
        monkeypatch.setattr(stream_parser, 'record_tokens', lambda *args: recorded.append(args))
        source = stream_parser.stream_generator({}, {}, deadline_seconds=.03)
        received = []
        async def consume():
            async for chunk in source:
                received.append(chunk)
                if mode == 'consumer_pause' and chunk == raw:
                    # Deadline is not allowed to cancel the consumer here.
                    await asyncio.sleep(.05)
        if mode == 'cancel':
            task = asyncio.create_task(consume())
            await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert received == []
        else:
            await consume()
            assert received[:-1] == ([raw] if mode in ('after', 'consumer_pause') else [])
            error = json.loads(received[-1][6:])['error']
            assert error['type'] == 'provider_deadline'
        assert opened == closed == [1] and recorded == []
    asyncio.run(scenario())


def test_consumer_close_after_chunk_releases_upstream(monkeypatch):
    async def scenario():
        closed = []
        class Response:
            headers = {}
            status_code = 200
            def raise_for_status(self):
                pass
            async def aiter_raw(self):
                yield b'data: fixture\n\n'
                await asyncio.Event().wait()
        class Context:
            async def __aenter__(self):
                return Response()
            async def __aexit__(self, *args):
                closed.append(1)
        class Client:
            def stream(self, *args, **kwargs):
                return Context()
        monkeypatch.setattr(stream_parser, 'client', Client())
        source = stream_parser.stream_generator({}, {})
        assert await anext(source) == b'data: fixture\n\n'
        await source.aclose()
        assert closed == [1]
    asyncio.run(scenario())
