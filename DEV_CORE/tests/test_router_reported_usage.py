"""Provider-boundary probes: no keys, stores, network or estimated usage."""
import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from router import providers
from router.usage import reported_usage


@pytest.mark.parametrize('usage,expected', [
    ({'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}, (0, 0)),
    ({'prompt_tokens': 7, 'completion_tokens': 3}, (7, 3)),
    (None, None), ({}, None), ({'prompt_tokens': 7}, None),
    ({'prompt_tokens': True, 'completion_tokens': 0}, None),
    ({'prompt_tokens': -1, 'completion_tokens': 2}, None),
    ({'prompt_tokens': '7', 'completion_tokens': 3}, None),
    ({'prompt_tokens': 7, 'completion_tokens': 3, 'total_tokens': 11}, None),
    ({'prompt_tokens': (1 << 63) - 1, 'completion_tokens': 1}, None),
])
def test_usage_validation_preserves_zero_and_refuses_incomplete_or_invalid(usage, expected):
    assert reported_usage({'usage': usage}) == expected


def test_embedding_usage_has_no_generated_completion():
    assert reported_usage({'usage': {'prompt_tokens': 7, 'total_tokens': 7}}, is_chat=False) == (7, 0)
    assert reported_usage([]) is None


@pytest.mark.parametrize('fallback', [False, True])
@pytest.mark.parametrize('usage', [None, {'prompt_tokens': 0, 'completion_tokens': 0},
    {'prompt_tokens': 7, 'completion_tokens': 3, 'total_tokens': 10}])
def test_response_is_preserved_and_only_reported_tokens_reach_stats(monkeypatch, fallback, usage):
    payload = {'choices': [{'message': {'content': 'private' * 1000}}]}
    if usage is not None:
        payload['usage'] = usage
    raw = json.dumps(payload).encode()
    upstream = httpx.Response(200, content=raw, request=httpx.Request('POST', 'https://fixture/v1/chat/completions'))
    posts, records, limits = [], [], []
    class Client:
        async def post(self, *args, **kwargs):
            posts.append(kwargs['json'])
            return upstream
    class Limiter:
        async def wait_if_needed(self, *args):
            pass
        async def record_tokens(self, tokens):
            limits.append(tokens)
    monkeypatch.setattr(providers, 'client', Client())
    monkeypatch.setattr(providers, 'rate_limiter', Limiter())
    monkeypatch.setattr(providers, 'fallback_limiters', {'cerebras': Limiter(), 'nvidia-nim': Limiter()})
    monkeypatch.setattr(providers, 'API_KEY', 'fixture' if not fallback else '')
    monkeypatch.setattr(providers, 'CEREBRAS_API_KEY', 'fixture' if fallback else '')
    monkeypatch.setattr(providers, 'NVIDIA_API_KEY', '')
    monkeypatch.setattr(providers, 'get_active_task_and_mode', lambda: ('T-fixture', 'documentation'))
    monkeypatch.setattr(providers, 'has_budget_alert', lambda task: False)
    monkeypatch.setattr(providers, 'record_tokens', lambda *args: records.append(args))
    body = {'model': 'devcore-summary', 'messages': [], 'fallback_providers': ['cerebras'] if fallback else []}
    result = asyncio.run(providers.call_with_fallback('chat/completions', body, {}, is_chat=True))
    assert result.body == raw and result.status_code == 200 and len(posts) == 1
    expected = [] if usage is None else [('unattributed.summary', 'summary', usage['prompt_tokens'], usage['completion_tokens'])]
    assert records == expected
    assert result.headers['x-devcore-usage-source'] == ('unavailable' if usage is None else 'provider_reported')
    assert limits == ([] if usage is None else [sum((usage['prompt_tokens'], usage['completion_tokens']))])


@pytest.fixture(autouse=True)
def substitute_provider_body_reader(monkeypatch):
    async def reader(client, url, *, json, headers):
        return await client.post(url, json=json, headers=headers)
    monkeypatch.setattr(providers, 'post_bounded', reader)
