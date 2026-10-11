"""ASGI admission precedes stream headers and provider calls."""
import asyncio
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from Scripts import gemini_router as router
from router.rate_limit import SlidingWindowRateLimiter, RateLimitRefusal


def test_stream_and_nonstream_share_saturation_and_refusal_precedes_generator(monkeypatch):
    async def scenario():
        limiter = SlidingWindowRateLimiter(max_rpm=1)
        monkeypatch.setattr(router.provider_state, 'rate_limiter', limiter)
        monkeypatch.setattr(router, 'API_KEY', 'fixture')
        monkeypatch.setattr(router.provider_state, 'API_KEY', 'fixture')
        class Client:
            async def post(self, *args, **kwargs):
                pytest.fail('Saturation must refuse before upstream')
        monkeypatch.setattr(router.provider_state, 'client', Client())
        monkeypatch.setattr(router, 'check_protocol_compliance',
            lambda: type('Status', (), {'compliant': True})())
        started = []
        async def stream(body, headers, *, limiter, estimated_tokens, accounting_mode):
            assert accounting_mode == "summary"
            started.append(body['model'])
            yield b'data: [DONE]\n\n'
        monkeypatch.setattr(router, 'stream_generator', stream)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=router.app), base_url='http://fixture') as client:
            first = await client.post('/v1/chat/completions', json={'model': 'devcore-summary', 'stream': True})
            assert first.status_code == 200 and first.content == b'data: [DONE]\n\n'
            second = await client.post('/v1/chat/completions', json={'model': 'devcore-summary', 'stream': True})
            assert second.status_code == 429 and int(second.headers['retry-after']) >= 1
            assert second.headers['content-type'].startswith('application/json')
            nonstream = await client.post('/v1/chat/completions', json={'model': 'devcore-summary'})
            assert nonstream.status_code == 429 and 'retry-after' in nonstream.headers
            with pytest.raises(RateLimitRefusal):
                await limiter.wait_if_needed(100)
            assert len(started) == 1
    asyncio.run(scenario())


def test_missing_key_and_native_refusal_do_not_consume_stream_reservations(monkeypatch):
    async def scenario():
        limiter = SlidingWindowRateLimiter()
        monkeypatch.setattr(router.provider_state, 'rate_limiter', limiter)
        monkeypatch.setattr(router, 'API_KEY', '')
        monkeypatch.setattr(router, 'check_protocol_compliance',
            lambda: type('Status', (), {'compliant': True})())
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=router.app), base_url='http://fixture') as client:
            unavailable = await client.post('/v1/chat/completions', json={'model': 'devcore-summary', 'stream': True})
            refused = await client.post('/v1/chat/completions', json={'model': 'gpt-test', 'stream': True})
            assert unavailable.status_code == 503 and refused.status_code == 400
            assert limiter.snapshot()['reserved_requests'] == 0
    asyncio.run(scenario())
