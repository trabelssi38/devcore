"""Fragmented SSE observations are bounded; forwarded chunks are untouched."""
import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from router.sse_usage import SseUsage
from router import stream_parser


def wire(usage):
    return b'data: ' + json.dumps({'usage': usage}).encode() + b'\r\n\r\ndata: [DONE]\r\n\r\n'


@pytest.mark.parametrize('size', [1, 2, 7, 65536])
def test_fragmented_crlf_events_preserve_reported_zero(size):
    raw = b': keepalive\r\n\r\n' + wire({'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0})
    observer = SseUsage()
    for start in range(0, len(raw), size):
        observer.feed(raw[start:start + size])
    assert observer.result() == (0, 0) and not observer.line and not observer.data


def test_multiline_data_and_missing_terminal_marker():
    raw = b'data: {"usage":\ndata: {"prompt_tokens":7,"completion_tokens":3}}\n\n'
    observer = SseUsage()
    observer.feed(raw)
    assert observer.result() is None
    observer.feed(b'data: [DONE]\n\n')
    assert observer.result() == (7, 3)


@pytest.mark.parametrize('raw', [b'data: nope\n\n', b'data: ' + b'x' * 65537,
    b''.join(b'data: ' + b'x' * 1024 + b'\n' for _ in range(65))],
    ids=['invalid_json', 'oversized_line', 'oversized_event'])
def test_invalid_or_oversized_observation_disables_without_retaining_text(raw):
    observer = SseUsage()
    observer.feed(raw)
    observer.feed(wire({'prompt_tokens': 7, 'completion_tokens': 3}))
    assert observer.disabled and observer.result() is None
    assert not observer.line and not observer.data


@pytest.mark.parametrize('mode', ['valid', 'absent', 'incomplete', 'error', 'cancelled', 'pre_error'])
def test_forwarding_preserves_chunks_no_estimation_or_retry_after_delivery(monkeypatch, capsys, mode):
    chunks = [b'data: {"choices":[{"delta":{"content":"private"}}]}\n\n']
    if mode == 'valid':
        raw = wire({'prompt_tokens': 7, 'completion_tokens': 3, 'total_tokens': 10})
        chunks += [raw[:13], raw[13:]]
    elif mode == 'absent':
        chunks += [b'data: [DONE]\n\n']
    records, attempts, totals = [], [], []
    class Limiter:
        async def wait_if_needed(self, *args):
            pass
        async def record_tokens(self, tokens):
            totals.append(tokens)
    class Response:
        headers = {}
        status_code = 200
        def raise_for_status(self):
            pass
        async def aiter_raw(self):
            if mode == 'pre_error':
                raise RuntimeError('private fixture failure before delivery')
            for chunk in chunks:
                yield chunk
            if mode == 'error':
                raise RuntimeError('fixture upstream failure')
            if mode == 'cancelled':
                raise asyncio.CancelledError()
    class Context:
        async def __aenter__(self):
            return Response()
        async def __aexit__(self, *args):
            pass
    class Client:
        def stream(self, *args, **kwargs):
            attempts.append(1)
            return Context()
    monkeypatch.setattr(stream_parser, 'client', Client())
    monkeypatch.setattr(stream_parser, 'get_active_task_and_mode', lambda: ('T-fixture', 'documentation'))
    monkeypatch.setattr(stream_parser, 'record_tokens', lambda *args: records.append(args))
    if mode == 'pre_error':
        async def no_delay(*args):
            pass
        monkeypatch.setattr(stream_parser.asyncio, 'sleep', no_delay)
    async def scenario():
        received = []
        async def consume():
            async for chunk in stream_parser.stream_generator({'messages': ['private']}, {}, limiter=Limiter()):
                received.append(chunk)
        if mode in ('error', 'cancelled'):
            with pytest.raises(RuntimeError if mode == 'error' else asyncio.CancelledError):
                await consume()
        else:
            await consume()
        if mode == 'pre_error':
            assert len(received) == 1 and 'error' in json.loads(received[0])
            assert attempts == [1, 1, 1]
        else:
            assert received == chunks and attempts == [1]
    asyncio.run(scenario())
    assert records == ([('unattributed.auxiliary', 'auxiliary', 7, 3)] if mode == 'valid' else [])
    assert totals == ([10] if mode == 'valid' else [])
    output = capsys.readouterr()
    assert 'private fixture failure' not in output.out + output.err


@pytest.mark.parametrize('kind', ['depth64', 'depth65', 'quoted'])
def test_sse_json_depth_disables_usage_without_retaining_content(kind):
    raw = (b'{"nested":' + b'[' * (63 if kind == 'depth64' else 64) + b'0' +
        b']' * (63 if kind == 'depth64' else 64) + b'}') if kind != 'quoted' else (
        json.dumps({'text': '[{' * 100 + '\"quoted\"'}).encode())
    observer = SseUsage()
    observer.feed(b'data: ' + raw + b'\n\n')
    observer.feed(wire({'prompt_tokens': 7, 'completion_tokens': 3}))
    if kind == 'depth65':
        assert observer.disabled and observer.result() is None
    else:
        assert not observer.disabled and observer.result() == (7, 3)
    assert not observer.line and not observer.data


@pytest.mark.parametrize('cancel', [False, True])
def test_large_sse_observation_leaves_other_work_available(cancel):
    async def scenario():
        observer = SseUsage()
        raw = b': keepalive\n\n' * 25000 + wire({'prompt_tokens': 7, 'completion_tokens': 3})
        task = asyncio.create_task(observer.feed_async(raw))
        await asyncio.sleep(0)
        assert not task.done() and observer.result() is None
        if cancel:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert observer.disabled and not observer.line and not observer.data
            observer.feed(wire({'prompt_tokens': 7, 'completion_tokens': 3}))
            assert observer.result() is None
        else:
            await task
            assert observer.result() == (7, 3)
    asyncio.run(scenario())
