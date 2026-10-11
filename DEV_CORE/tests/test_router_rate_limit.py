import asyncio
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from router.rate_limit import SlidingWindowRateLimiter, RateLimitRefusal
from router import providers


def test_concurrent_admission_has_no_wait_and_reopens_at_expiry():
    async def scenario():
        now = [0.0]
        limiter = SlidingWindowRateLimiter(max_rpm=2, max_tpm=100, clock=lambda: now[0])
        async def admit():
            try:
                await limiter.wait_if_needed(10)
                return 'ok'
            except RateLimitRefusal as exc:
                assert exc.retry_after == 60
                return 'refused'
        results = await asyncio.gather(*(admit() for _ in range(20)))
        assert results.count('ok') == 2 and results.count('refused') == 18
        await limiter.record_tokens(5)  # Refused requests do not hold a lock.
        now[0] = 60.0
        await limiter.wait_if_needed(100)
        assert limiter.snapshot()['reserved_requests'] == 1
    asyncio.run(scenario())


def test_estimates_reserved_and_reports_conservatively_bounded():
    async def scenario():
        now = [0.2]
        limiter = SlidingWindowRateLimiter(max_rpm=4096, max_tpm=100, clock=lambda: now[0])
        await limiter.wait_if_needed(80)
        with pytest.raises(RateLimitRefusal):
            await limiter.wait_if_needed(21)
        for _ in range(10000):
            await limiter.record_tokens(1)
        assert limiter.snapshot()['reported_buckets'] == 1
        now[0] = 60.2
        with pytest.raises(RateLimitRefusal):
            await limiter.wait_if_needed(1)
        now[0] = 61
        await limiter.wait_if_needed(100)
        assert limiter.snapshot()['reported_buckets'] == 0
    asyncio.run(scenario())


@pytest.mark.parametrize('value', [True, -1, '1', 1.0, 1 << 63])
def test_invalid_counts_are_refused_without_admission(value):
    async def scenario():
        limiter = SlidingWindowRateLimiter()
        with pytest.raises(ValueError):
            await limiter.wait_if_needed(value)
        with pytest.raises(ValueError):
            await limiter.record_tokens(value)
        assert limiter.snapshot()['reserved_requests'] == 0
    asyncio.run(scenario())


def test_local_refusal_never_calls_provider_or_authorized_fallback(monkeypatch):
    async def scenario():
        limiter = SlidingWindowRateLimiter(max_rpm=1)
        await limiter.wait_if_needed(1)
        monkeypatch.setattr(providers, 'rate_limiter', limiter)
        monkeypatch.setattr(providers, 'API_KEY', 'fixture')
        monkeypatch.setattr(providers, 'CEREBRAS_API_KEY', 'fixture')
        class Client:
            async def post(self, *args, **kwargs):
                pytest.fail('No provider call permitted after local refusal')
        monkeypatch.setattr(providers, 'client', Client())
        result = await providers.call_with_fallback('chat/completions', {
            'model': 'devcore-summary', 'messages': [], 'fallback_providers': ['cerebras']}, {}, True)
        assert result.status_code == 429 and 1 <= int(result.headers['retry-after']) <= 61
        assert b'local_rate_limit' in result.body
    asyncio.run(scenario())
