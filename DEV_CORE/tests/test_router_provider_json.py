"""Provider JSON is checked before success or usage side effects."""
import asyncio
import json
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from router import providers


@pytest.mark.parametrize('fallback', [False, True])
@pytest.mark.parametrize('kind', ['depth64', 'depth65', 'quoted', 'syntax', 'utf8', 'array'])
def test_provider_json_bounds_are_terminal_and_preserve_valid_bytes(monkeypatch, fallback, kind):
    raw = {
        'depth64': b'{"nested":' + b'[' * 63 + b'0' + b']' * 63 + b'}',
        'depth65': b'{"nested":' + b'[' * 64 + b'0' + b']' * 64 + b'}',
        'quoted': json.dumps({'text': '[{' * 100 + '\"quoted\"'}).encode(),
        'syntax': b'{PRIVATE_fixture', 'utf8': b'{"text":"\xff"}', 'array': b'[]',
    }[kind]
    calls, records = [], []
    class Limiter:
        async def wait_if_needed(self, *args):
            pass
    async def reader(*args, **kwargs):
        calls.append(1)
        return httpx.Response(200, content=raw, request=httpx.Request('POST', 'https://fixture'))
    monkeypatch.setattr(providers, 'post_bounded', reader)
    monkeypatch.setattr(providers, 'rate_limiter', Limiter())
    monkeypatch.setattr(providers, 'fallback_limiters', {'cerebras': Limiter(), 'nvidia-nim': Limiter()})
    monkeypatch.setattr(providers, 'API_KEY', '' if fallback else 'fixture')
    monkeypatch.setattr(providers, 'CEREBRAS_API_KEY', 'fixture')
    monkeypatch.setattr(providers, 'NVIDIA_API_KEY', 'fixture')
    monkeypatch.setattr(providers, 'get_active_task_and_mode', lambda: ('fixture', 'summary'))
    monkeypatch.setattr(providers, 'has_budget_alert', lambda *args: False)
    monkeypatch.setattr(providers, 'record_tokens', lambda *args: records.append(args))
    result = asyncio.run(providers.call_with_fallback('chat/completions', {
        'model': 'devcore-summary', 'messages': [], 'fallback_providers': ['cerebras', 'nvidia']}, {}, True))
    assert calls == [1] and records == []
    if kind in ('depth64', 'quoted'):
        assert result.status_code == 200 and result.body == raw
    else:
        assert result.status_code == 502 and b'provider_response_refused' in result.body
        assert b'PRIVATE_fixture' not in result.body


def test_large_json_scan_can_be_cancelled_without_finishing():
    async def scenario():
        raw = json.dumps({'text': 'x' * 200000}).encode()
        task = asyncio.create_task(providers.decode_provider_json(raw))
        await asyncio.sleep(0)
        assert not task.done()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(scenario())
