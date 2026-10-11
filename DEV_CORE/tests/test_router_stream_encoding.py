"""Real HTTPX stream refuses compression before reading or retrying."""
import asyncio
import json
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from router import stream_parser


@pytest.mark.parametrize('encoding', [None, 'identity', 'gzip', 'br', 'GZip'])
def test_identity_transport_and_terminal_compression_refusal(monkeypatch, encoding):
    async def scenario():
        reads, closes, calls, records = [], [], [], []
        raw = b'data: {"usage":{"prompt_tokens":7,"completion_tokens":3}}\n\ndata: [DONE]\n\n'
        class Stream(httpx.AsyncByteStream):
            async def __aiter__(self):
                reads.append(1)
                yield raw[:10]
                yield raw[10:]
            async def aclose(self):
                closes.append(1)
        def handle(request):
            calls.append(1)
            assert request.headers['accept-encoding'] == 'identity'
            headers = {'Content-Encoding': encoding} if encoding else {}
            return httpx.Response(200, headers=headers, stream=Stream())
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            monkeypatch.setattr(stream_parser, 'client', client)
            monkeypatch.setattr(stream_parser, 'get_active_task_and_mode', lambda: ('fixture', 'summary'))
            monkeypatch.setattr(stream_parser, 'record_tokens', lambda *args: records.append(args))
            chunks = [chunk async for chunk in stream_parser.stream_generator({}, {})]
        assert calls == closes == [1]
        if encoding in (None, 'identity'):
            assert chunks == [raw[:10], raw[10:]] and reads == [1]
            assert records == [('unattributed.auxiliary', 'auxiliary', 7, 3)]
        else:
            assert reads == [] and records == [] and len(chunks) == 1
            assert json.loads(chunks[0][6:])['error']['type'] == 'provider_response_refused'
            assert len(chunks[0]) < 256
    asyncio.run(scenario())
