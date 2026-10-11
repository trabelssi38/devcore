"""Provider failure messages never echo body or raw exception markers."""
import asyncio
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from router import providers


@pytest.mark.parametrize('provider', ['gemini', 'cerebras', 'nvidia'])
def test_failure_logs_and_public_error_omit_private_details(monkeypatch, capsys, provider):
    marker = 'PRIVATE_fixture_credentials_and_prompt'
    calls = []
    class Limiter:
        async def wait_if_needed(self, *args):
            pass
    class Client:
        async def post(self, *args, **kwargs):
            calls.append(1)
            if provider != 'nvidia':
                raise RuntimeError(marker)
            return httpx.Response(500, text=marker)
    async def no_delay(*args):
        pass
    monkeypatch.setattr(providers.asyncio, 'sleep', no_delay)
    monkeypatch.setattr(providers, 'client', Client())
    monkeypatch.setattr(providers, 'rate_limiter', Limiter())
    monkeypatch.setattr(providers, 'fallback_limiters', {'cerebras': Limiter(), 'nvidia-nim': Limiter()})
    monkeypatch.setattr(providers, 'API_KEY', 'fixture' if provider == 'gemini' else '')
    monkeypatch.setattr(providers, 'CEREBRAS_API_KEY', 'fixture' if provider == 'cerebras' else '')
    monkeypatch.setattr(providers, 'NVIDIA_API_KEY', 'fixture' if provider == 'nvidia' else '')
    result = asyncio.run(providers.call_with_fallback('chat/completions', {
        'model': 'devcore-summary', 'messages': [],
        'fallback_providers': [] if provider == 'gemini' else [provider]}, {}, True))
    captured = capsys.readouterr()
    assert result.status_code == 502 and marker.encode() not in result.body
    assert marker not in captured.out + captured.err
    assert 'GeminiRouter' in captured.out and len(calls) == (3 if provider == 'gemini' else 1)


@pytest.fixture(autouse=True)
def substitute_provider_body_reader(monkeypatch):
    async def reader(client, url, *, json, headers):
        return await client.post(url, json=json, headers=headers)
    monkeypatch.setattr(providers, 'post_bounded', reader)
