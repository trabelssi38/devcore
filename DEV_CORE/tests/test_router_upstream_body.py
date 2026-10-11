import asyncio
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from router.upstream_body import post_bounded, UpstreamBodyRefusal
from router import providers


@pytest.mark.parametrize('mode', ['exact', 'overflow', 'declared', 'gzip', 'error', 'cancel'])
def test_reader_closes_uncompressed_stream_and_bounds_body(mode):
    async def scenario():
        closed, reads = [], []
        entered = asyncio.Event()
        class Stream(httpx.AsyncByteStream):
            async def __aiter__(self):
                reads.append(1)
                entered.set()
                if mode == 'cancel':
                    await asyncio.Event().wait()
                yield b'1234'
                yield b'56789' if mode == 'overflow' else b'5678'
            async def aclose(self):
                closed.append(1)
        def handle(request):
            assert request.headers['accept-encoding'] == 'identity'
            headers = {'Content-Encoding': 'gzip'} if mode == 'gzip' else (
                {'Content-Length': '9'} if mode == 'declared' else {})
            return httpx.Response(500 if mode == 'error' else 200, headers=headers, stream=Stream())
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            task = asyncio.create_task(post_bounded(client, 'https://fixture', json={}, headers={}, max_bytes=8))
            if mode == 'cancel':
                await entered.wait()
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            elif mode in ('overflow', 'declared', 'gzip'):
                with pytest.raises(UpstreamBodyRefusal):
                    await task
            else:
                response = await task
                assert response.content == (b'' if mode == 'error' else b'12345678')
            assert closed == [1]
            if mode in ('error', 'declared', 'gzip'):
                assert reads == []
    asyncio.run(scenario())


@pytest.mark.parametrize('fallback', [False, True])
def test_transport_refusal_is_terminal_without_retry_or_other_provider(monkeypatch, fallback):
    async def scenario():
        calls = []
        class Limiter:
            async def wait_if_needed(self, *args):
                pass
        async def refuse(*args, **kwargs):
            calls.append(1)
            raise UpstreamBodyRefusal('private details')
        monkeypatch.setattr(providers, 'post_bounded', refuse)
        monkeypatch.setattr(providers, 'rate_limiter', Limiter())
        monkeypatch.setattr(providers, 'fallback_limiters', {'cerebras': Limiter(), 'nvidia-nim': Limiter()})
        monkeypatch.setattr(providers, 'API_KEY', '' if fallback else 'fixture')
        monkeypatch.setattr(providers, 'CEREBRAS_API_KEY', 'fixture')
        monkeypatch.setattr(providers, 'NVIDIA_API_KEY', 'fixture')
        response = await providers.call_with_fallback('chat/completions', {
            'model': 'devcore-summary', 'messages': [], 'fallback_providers': ['cerebras', 'nvidia']}, {}, True)
        assert response.status_code == 502 and calls == [1]
        assert b'provider_response_refused' in response.body and b'private' not in response.body
    asyncio.run(scenario())


@pytest.mark.parametrize('size', [1, 65536])
@pytest.mark.parametrize('cancel', [False, True])
def test_buffered_transport_yields_to_other_work_and_cancellation(size, cancel):
    async def scenario():
        reads, closed, progress = [], [], []
        class Stream(httpx.AsyncByteStream):
            async def __aiter__(self):
                for _ in range(128):
                    reads.append(1)
                    yield b'x' * size
            async def aclose(self):
                closed.append(1)
        def handle(request):
            return httpx.Response(200, stream=Stream())
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            reader = asyncio.create_task(post_bounded(client, 'https://fixture', json={}, headers={}))
            async def other_work():
                progress.append(len(reads))
                if cancel:
                    reader.cancel()
            competitor = asyncio.create_task(other_work())
            await competitor
            if cancel:
                with pytest.raises(asyncio.CancelledError):
                    await reader
                assert len(reads) < 128
            else:
                response = await reader
                assert response.content == b'x' * (128 * size)
            assert 0 < progress[0] <= (64 if size == 1 else 1)
            assert closed == [1]
    asyncio.run(scenario())
