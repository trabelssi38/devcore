"""Byte capacity rejects whole exceeding chunks and closes upstream."""
import asyncio
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from router import stream_parser


@pytest.mark.parametrize('sizes,expected', [([4, 4], [4, 4]), ([4, 5], [4]), ([9], [])])
def test_boundary_or_excess_preserves_only_complete_accepted_chunks(monkeypatch, sizes, expected):
    async def scenario():
        closed, opened, records = [], [], []
        class Response:
            headers = {}
            status_code = 200
            def raise_for_status(self):
                pass
            async def aiter_raw(self):
                for size in sizes:
                    yield b'x' * size
        class Context:
            async def __aenter__(self):
                opened.append(1)
                return Response()
            async def __aexit__(self, *args):
                closed.append(1)
        class Client:
            def stream(self, *args, **kwargs):
                return Context()
        monkeypatch.setattr(stream_parser, 'client', Client())
        monkeypatch.setattr(stream_parser, 'record_tokens', lambda *args: records.append(args))
        chunks = [chunk async for chunk in stream_parser.stream_generator({}, {}, max_response_bytes=8)]
        exceeded = sum(sizes) > 8
        forwarded = chunks[:-1] if exceeded else chunks
        assert forwarded == [b'x' * size for size in expected]
        if exceeded:
            assert json.loads(chunks[-1][6:])['error']['type'] == 'provider_response_too_large'
            assert len(chunks[-1]) < 256
        assert opened == closed == [1] and records == []
    asyncio.run(scenario())


@pytest.mark.parametrize('capacity', [True, 0, -1, 1.5, 16 * 1024 * 1024 + 1])
def test_invalid_capacity_refused_before_upstream(capacity):
    async def scenario():
        with pytest.raises(ValueError):
            await anext(stream_parser.stream_generator({}, {}, max_response_bytes=capacity))
    asyncio.run(scenario())
