"""Auxiliary routes must never consult a shared active task or inject reminders."""
import asyncio
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
import gemini_router as router
from router import providers, stream_parser


def test_retired_shared_protocol_helpers_fail_closed(tmp_path):
    runtime = tmp_path / 'Runtime'
    memory = tmp_path / 'Memory' / 'alpha'
    runtime.mkdir()
    memory.mkdir(parents=True)
    active = runtime / 'active_project.txt'
    board = memory / 'tasks.json'
    active.write_text('alpha', encoding='utf-8')
    board.write_text('{"current_task":"T-01"}', encoding='utf-8')
    before = (active.read_bytes(), board.read_bytes())
    with pytest.raises(RuntimeError, match='retired'):
        providers.get_active_task_and_mode()
    with pytest.raises(RuntimeError, match='retired'):
        providers.check_protocol_compliance()
    with pytest.raises(RuntimeError, match='retired'):
        providers.inject_protocol_reminder({'messages': []},
            providers.ProtocolStatus(False, 'T-01', 'coding', True, 1))
    with pytest.raises(RuntimeError, match='retired'):
        providers.log_protocol_violation(
            providers.ProtocolStatus(False, 'T-01', 'coding', True, 1))
    assert (active.read_bytes(), board.read_bytes()) == before
    assert sorted(path.name for path in runtime.iterdir()) == ['active_project.txt']


@pytest.mark.parametrize('route', ['chat', 'stream', 'embedding', 'fallback'])
def test_routes_preserve_inputs_and_mark_usage_unattributed(monkeypatch, route):
    async def scenario():
        calls, records = [], []
        def forbidden(*args, **kwargs):
            raise AssertionError('Shared project/task state must not be consulted')
        for module, name in ((router, 'check_protocol_compliance'), (router, 'inject_protocol_reminder'),
            (router, 'log_protocol_violation'), (providers, 'get_active_task_and_mode'),
            (stream_parser, 'get_active_task_and_mode')):
            monkeypatch.setattr(module, name, forbidden)
        class Limiter:
            async def wait_if_needed(self, *args):
                pass
            async def record_tokens(self, *args):
                pass
        usage = {'prompt_tokens': 7, 'completion_tokens': 3, 'total_tokens': 10}
        async def reader(client, url, *, json, headers):
            calls.append(json)
            return httpx.Response(200, json={'choices': [], 'usage': usage}, request=httpx.Request('POST', url))
        class Stream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b'data: {"usage":{"prompt_tokens":7,"completion_tokens":3}}\n\ndata: [DONE]\n\n'
        def handle(request):
            import json
            calls.append(json.loads(request.content))
            return httpx.Response(200, stream=Stream())
        monkeypatch.setattr(providers, 'post_bounded', reader)
        monkeypatch.setattr(providers, 'API_KEY', '' if route == 'fallback' else 'fixture')
        monkeypatch.setattr(providers, 'CEREBRAS_API_KEY', 'fixture')
        monkeypatch.setattr(providers, 'NVIDIA_API_KEY', '')
        monkeypatch.setattr(router, 'API_KEY', 'fixture')
        monkeypatch.setattr(providers, 'rate_limiter', Limiter())
        monkeypatch.setattr(providers, 'fallback_limiters', {'cerebras': Limiter()})
        monkeypatch.setattr(providers, 'has_budget_alert', lambda *args: False)
        monkeypatch.setattr(providers, 'record_tokens', lambda *args: records.append(args))
        monkeypatch.setattr(stream_parser, 'record_tokens', lambda *args: records.append(args))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as upstream:
            monkeypatch.setattr(stream_parser, 'client', upstream)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=router.app), base_url='http://fixture') as client:
                for user in ('alpha', 'beta'):
                    body = {'model': 'gemini-embedding-001', 'input': user} if route == 'embedding' else {
                        'model': 'devcore-documentation', 'messages': [{'role': 'user', 'content': user}]}
                    if route == 'stream': body['stream'] = True
                    if route == 'fallback': body['fallback_providers'] = ['cerebras']
                    result = await client.post('/v1/embeddings' if route == 'embedding' else '/v1/chat/completions', json=body)
                    assert result.status_code == 200
                    assert result.headers['x-devcore-attribution'] == 'unattributed'
                    if route == 'embedding': assert calls[-1]['input'] == user
                    else: assert calls[-1]['messages'] == body['messages']
        mode = 'embedding' if route == 'embedding' else 'documentation'
        assert records == [('unattributed.' + mode, mode, 7, 3)] * 2
    asyncio.run(scenario())
