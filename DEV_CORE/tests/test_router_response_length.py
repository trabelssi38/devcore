"""Length declarations are checked before read and before success accounting."""
import asyncio
import json
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from router import stream_parser
from router.upstream_body import post_bounded, UpstreamBodyRefusal


@pytest.mark.parametrize('streaming', [False, True])
@pytest.mark.parametrize('kind', ['exact', 'zeros', 'absent', 'huge', 'empty', 'multiple', 'negative', 'over', 'under', 'protocol'])
def test_length_refusal_closes_transport_without_retry_or_false_usage(monkeypatch, streaming, kind):
    async def scenario():
        raw = b'data: {"usage":{"prompt_tokens":7,"completion_tokens":3}}\n\ndata: [DONE]\n\n'
        length = {'exact': str(len(raw)), 'zeros': '0' * 5000 + str(len(raw)),
            'absent': None, 'protocol': None, 'huge': '9' * 5000, 'empty': '', 'multiple': '8, 8',
            'negative': '-1', 'over': str(len(raw) + 1), 'under': str(len(raw) - 1)}[kind]
        reads, closed, calls, records = [], [], [], []
        class Stream(httpx.AsyncByteStream):
            async def __aiter__(self):
                reads.append(1)
                yield raw[:10]
                if kind == 'protocol':
                    raise httpx.RemoteProtocolError('private framing details')
                yield raw[10:]
            async def aclose(self):
                closed.append(1)
        def handle(request):
            calls.append(1)
            headers = {'Content-Length': length} if length is not None else {}
            return httpx.Response(200, headers=headers, stream=Stream())
        valid = kind in ('exact', 'zeros', 'absent')
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            if streaming:
                monkeypatch.setattr(stream_parser, 'client', client)
                monkeypatch.setattr(stream_parser, 'get_active_task_and_mode', lambda: ('fixture', 'summary'))
                monkeypatch.setattr(stream_parser, 'record_tokens', lambda *args: records.append(args))
                chunks = [chunk async for chunk in stream_parser.stream_generator({}, {}, max_response_bytes=len(raw) + 2)]
                if valid:
                    assert chunks == [raw[:10], raw[10:]] and records == [('unattributed.auxiliary', 'auxiliary', 7, 3)]
                else:
                    assert json.loads(chunks[-1][6:])['error']['type'] == 'provider_response_refused'
                    assert records == []
                    assert chunks[:-1] == ([raw[:10], raw[10:]] if kind == 'over' else [raw[:10]] if kind in ('under', 'protocol') else [])
            elif valid:
                result = await post_bounded(client, 'https://fixture', json={}, headers={}, max_bytes=len(raw) + 2)
                assert result.content == raw
            else:
                with pytest.raises(UpstreamBodyRefusal):
                    await post_bounded(client, 'https://fixture', json={}, headers={}, max_bytes=len(raw) + 2)
        assert calls == closed == [1]
        assert reads == ([] if kind in ('huge', 'empty', 'multiple', 'negative') else [1])
    asyncio.run(scenario())
