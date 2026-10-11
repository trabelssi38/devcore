"""Total async deadline does not restart for retries or fallback providers."""
import asyncio
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from router import providers


def configure(monkeypatch, client, fallback=False):
    class Limiter:
        async def wait_if_needed(self, *args):
            pass
    monkeypatch.setattr(providers, 'client', client)
    monkeypatch.setattr(providers, 'rate_limiter', Limiter())
    monkeypatch.setattr(providers, 'fallback_limiters', {'cerebras': Limiter(), 'nvidia-nim': Limiter()})
    monkeypatch.setattr(providers, 'API_KEY', '' if fallback else 'fixture')
    monkeypatch.setattr(providers, 'CEREBRAS_API_KEY', 'fixture' if fallback else '')
    monkeypatch.setattr(providers, 'NVIDIA_API_KEY', '')
    monkeypatch.setattr(providers, 'get_active_task_and_mode', lambda: ('T-fixture', 'summary'))
    monkeypatch.setattr(providers, 'has_budget_alert', lambda task: False)
    return {'model': 'devcore-summary', 'messages': [], 'fallback_providers': ['cerebras'] if fallback else []}


@pytest.mark.parametrize('mode', ['gemini', 'fallback', 'retry_after'])
def test_deadline_stops_slow_chain_and_fast_request_remains_available(monkeypatch, mode):
    async def scenario():
        entered, cancelled = asyncio.Event(), asyncio.Event()
        calls = []
        class Client:
            async def post(self, url, **kwargs):
                slow = kwargs['json']['messages'] == ['slow']
                calls.append(slow)
                if not slow:
                    return httpx.Response(200, json={'choices': []}, request=httpx.Request('POST', url))
                entered.set()
                if mode == 'retry_after':
                    return httpx.Response(429, headers={'Retry-After': '3600'})
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    cancelled.set()
                    raise
        body = configure(monkeypatch, Client(), fallback=mode == 'fallback')
        slow = asyncio.create_task(providers.call_with_fallback('chat/completions',
            {**body, 'messages': ['slow']}, {}, True, deadline_seconds=.03))
        await entered.wait()
        fast = await providers.call_with_fallback('chat/completions', body, {}, True, deadline_seconds=.03)
        assert fast.status_code == 200
        expired = await slow
        assert expired.status_code == 504 and b'provider_deadline' in expired.body
        assert calls == [True, False]  # No second attempt or provider after expiry.
        if mode != 'retry_after':
            assert cancelled.is_set()
    asyncio.run(scenario())


def test_external_cancellation_is_not_translated_into_timeout(monkeypatch):
    async def scenario():
        entered, cancelled = asyncio.Event(), asyncio.Event()
        class Client:
            async def post(self, *args, **kwargs):
                entered.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    cancelled.set()
                    raise
        body = configure(monkeypatch, Client())
        task = asyncio.create_task(providers.call_with_fallback('chat/completions', body, {}, True))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cancelled.is_set()
    asyncio.run(scenario())


@pytest.mark.parametrize('deadline', [True, 0, 121, float('nan')])
def test_invalid_deadline_refused_before_provider(deadline):
    with pytest.raises(ValueError):
        asyncio.run(providers.call_with_fallback('chat/completions', {}, {}, True, deadline_seconds=deadline))


@pytest.fixture(autouse=True)
def substitute_provider_body_reader(monkeypatch):
    async def reader(client, url, *, json, headers):
        return await client.post(url, json=json, headers=headers)
    monkeypatch.setattr(providers, 'post_bounded', reader)
