"""Fallback quotas are independent, with no bypass on local refusal."""
import asyncio
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from router import providers
from router.rate_limit import SlidingWindowRateLimiter


@pytest.mark.parametrize('provider', ['cerebras', 'nvidia-nim'])
def test_saturated_fallback_never_calls_network_or_next_provider(monkeypatch, provider):
    async def scenario():
        limits = {name: SlidingWindowRateLimiter(max_rpm=1) for name in ('cerebras', 'nvidia-nim')}
        await limits[provider].wait_if_needed(100)
        monkeypatch.setattr(providers, 'fallback_limiters', limits)
        monkeypatch.setattr(providers, 'API_KEY', '')
        monkeypatch.setattr(providers, 'CEREBRAS_API_KEY', 'fixture' if provider == 'cerebras' else '')
        monkeypatch.setattr(providers, 'NVIDIA_API_KEY', 'fixture')
        class Client:
            async def post(self, *args, **kwargs):
                pytest.fail('No network on local refusal, including another fallback')
        monkeypatch.setattr(providers, 'client', Client())
        result = await providers.call_with_fallback('chat/completions', {
            'model': 'devcore-summary', 'messages': [], 'fallback_providers': ['cerebras', 'nvidia']}, {}, True)
        assert result.status_code == 429 and 1 <= int(result.headers['retry-after']) <= 61
        other = 'nvidia-nim' if provider == 'cerebras' else 'cerebras'
        assert limits[other].snapshot()['reserved_requests'] == 0
    asyncio.run(scenario())


def test_authorized_upstream_failure_can_use_independently_admitted_fallback(monkeypatch):
    async def scenario():
        limits = {name: SlidingWindowRateLimiter(max_rpm=1) for name in ('cerebras', 'nvidia-nim')}
        monkeypatch.setattr(providers, 'fallback_limiters', limits)
        monkeypatch.setattr(providers, 'API_KEY', '')
        monkeypatch.setattr(providers, 'CEREBRAS_API_KEY', 'fixture')
        monkeypatch.setattr(providers, 'NVIDIA_API_KEY', 'fixture')
        monkeypatch.setattr(providers, 'get_active_task_and_mode', lambda: ('T-fixture', 'summary'))
        monkeypatch.setattr(providers, 'has_budget_alert', lambda task: False)
        records, calls = [], []
        monkeypatch.setattr(providers, 'record_tokens', lambda *args: records.append(args))
        class Client:
            async def post(self, url, **kwargs):
                calls.append(url)
                return httpx.Response(500 if len(calls) == 1 else 200,
                    json={'usage': {'prompt_tokens': 7, 'completion_tokens': 3, 'total_tokens': 10}})
        monkeypatch.setattr(providers, 'client', Client())
        result = await providers.call_with_fallback('chat/completions', {
            'model': 'devcore-summary', 'messages': [], 'fallback_providers': ['cerebras', 'nvidia']}, {}, True)
        assert result.status_code == 200 and result.headers['x-devcore-provider'] == 'nvidia-nim'
        assert len(calls) == 2 and all(limit.snapshot()['reserved_requests'] == 1 for limit in limits.values())
        assert limits['cerebras'].snapshot()['reported_buckets'] == 0
        assert limits['nvidia-nim'].snapshot()['reported_buckets'] == 1
        assert records == [('unattributed.summary', 'summary', 7, 3)]
    asyncio.run(scenario())


def test_unapproved_fallback_does_not_reserve_or_call_provider(monkeypatch):
    async def scenario():
        limits = {name: SlidingWindowRateLimiter() for name in ('cerebras', 'nvidia-nim')}
        monkeypatch.setattr(providers, 'fallback_limiters', limits)
        monkeypatch.setattr(providers, 'API_KEY', '')
        monkeypatch.setattr(providers, 'CEREBRAS_API_KEY', 'fixture')
        monkeypatch.setattr(providers, 'NVIDIA_API_KEY', 'fixture')
        class Client:
            async def post(self, *args, **kwargs):
                pytest.fail('No explicitly authorized fallback')
        monkeypatch.setattr(providers, 'client', Client())
        result = await providers.call_with_fallback('chat/completions', {
            'model': 'devcore-summary', 'messages': []}, {}, True)
        assert result.status_code == 502
        assert all(limit.snapshot()['reserved_requests'] == 0 for limit in limits.values())
    asyncio.run(scenario())


@pytest.fixture(autouse=True)
def substitute_provider_body_reader(monkeypatch):
    async def reader(client, url, *, json, headers):
        return await client.post(url, json=json, headers=headers)
    monkeypatch.setattr(providers, 'post_bounded', reader)
