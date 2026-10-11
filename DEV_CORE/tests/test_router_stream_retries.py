"""Retry admission uses a real limiter and substituted upstream only."""
import asyncio
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from router import stream_parser
from router.rate_limit import SlidingWindowRateLimiter


@pytest.mark.parametrize('failure', [429, 500, 'transport'])
def test_saturated_retry_emits_bounded_sse_error_without_second_call(monkeypatch, capsys, failure):
    calls, records = [], []
    class Response:
        headers = {}
        status_code = failure
    class Context:
        async def __aenter__(self):
            if failure == 'transport':
                raise RuntimeError('private transport details')
            return Response()
        async def __aexit__(self, *args):
            pass
    class Client:
        def stream(self, *args, **kwargs):
            calls.append(1)
            return Context()
    async def no_delay(*args):
        pass
    monkeypatch.setattr(stream_parser.asyncio, 'sleep', no_delay)
    monkeypatch.setattr(stream_parser, 'client', Client())
    monkeypatch.setattr(stream_parser, 'record_tokens', lambda *args: records.append(args))
    async def scenario():
        limiter = SlidingWindowRateLimiter(max_rpm=1)
        await limiter.wait_if_needed(100)  # The route reserved the first attempt.
        chunks = [chunk async for chunk in stream_parser.stream_generator({}, {},
            limiter=limiter, estimated_tokens=100)]
        assert calls == [1] and len(chunks) == 1 and chunks[0].startswith(b'data: ')
        error = json.loads(chunks[0][6:])['error']
        assert error['type'] == 'local_rate_limit' and 1 <= error['retry_after'] <= 61
        assert b'private' not in chunks[0] and len(chunks[0]) < 512
        assert limiter.snapshot()['reserved_requests'] == 1
    asyncio.run(scenario())
    assert records == []
    output = capsys.readouterr()
    assert 'private transport details' not in output.out + output.err


def test_admitted_retry_preserves_stream_and_records_success_once(monkeypatch):
    calls, records = [], []
    raw = b'data: {"usage":{"prompt_tokens":7,"completion_tokens":3}}\n\ndata: [DONE]\n\n'
    class Response:
        headers = {}
        def __init__(self, status):
            self.status_code = status
        def raise_for_status(self):
            pass
        async def aiter_raw(self):
            yield raw
    class Context:
        async def __aenter__(self):
            return Response(500 if len(calls) == 1 else 200)
        async def __aexit__(self, *args):
            pass
    class Client:
        def stream(self, *args, **kwargs):
            calls.append(1)
            return Context()
    async def no_delay(*args):
        pass
    monkeypatch.setattr(stream_parser.asyncio, 'sleep', no_delay)
    monkeypatch.setattr(stream_parser, 'client', Client())
    monkeypatch.setattr(stream_parser, 'get_active_task_and_mode', lambda: ('T-fixture', 'summary'))
    monkeypatch.setattr(stream_parser, 'record_tokens', lambda *args: records.append(args))
    async def scenario():
        limiter = SlidingWindowRateLimiter(max_rpm=3)
        await limiter.wait_if_needed(100)
        chunks = [chunk async for chunk in stream_parser.stream_generator({}, {},
            limiter=limiter, estimated_tokens=100)]
        assert chunks == [raw] and calls == [1, 1]
        assert limiter.snapshot()['reserved_requests'] == 2
        assert limiter.snapshot()['reported_buckets'] == 1
    asyncio.run(scenario())
    assert records == [('unattributed.auxiliary', 'auxiliary', 7, 3)]
