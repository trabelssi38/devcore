"""Auxiliary ASGI route and loopback OTLP, without real providers or data."""
import asyncio
import json
from pathlib import Path
import sys

import httpx
import pytest
from fastapi import Response

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from devcore_api.correlation import CorrelationContext
from devcore_api.llmops_generation import GenerationObserver
from devcore_api.otlp_worker import OtlpWorker
from devcore_api.router_generation import event_from_chat_response
from test_otlp_export import exporter, receiver
from Scripts import gemini_router as router


def response(**changes):
    payload = {'model': 'gemini-2.5-flash', 'choices': [{'message': {'content': 'private'}}],
        'usage': {'prompt_tokens': 7, 'completion_tokens': 3, 'total_tokens': 10}}
    payload.update(changes)
    return Response(json.dumps(payload), media_type='application/json', headers={
        'X-DevCore-Route': 'auxiliary', 'X-DevCore-Resolved-Model': 'gemini-2.5-flash'})


def adapter(result, cost=.01):
    return event_from_chat_response(result, cost_usd=cost,
        correlation=CorrelationContext(trace_id='1' * 32, project_id='alpha', task_id='T-1'))


def test_asgi_generation_returns_before_ack_and_exports_response_usage(monkeypatch):
    with receiver(delayed=True) as (endpoint, calls, entered, release):
        async def scenario():
            worker = OtlpWorker(exporter(endpoint))
            worker.start()
            observer = GenerationObserver(worker)
            monkeypatch.setattr(router.app.state, 'generation_observer', observer, raising=False)
            monkeypatch.setattr(router.app.state, 'generation_event_factory',
                lambda request, result: adapter(result), raising=False)
            monkeypatch.setattr(router, 'check_protocol_compliance',
                lambda: type('Status', (), {'compliant': True})())
            operations = []
            async def completion(path, body, headers, is_chat):
                operations.append(body['model'])
                return response()
            monkeypatch.setattr(router, 'call_with_fallback', completion)
            try:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=router.app),
                    base_url='http://fixture') as client:
                    result = await client.post('/v1/chat/completions', json={'model': 'devcore-summary'})
                    assert result.status_code == 200 and result.json()['choices'][0]['message']['content'] == 'private'
                    assert await asyncio.to_thread(entered.wait, 1)
                    assert worker.snapshot()['accepted'] == 0
                    refused = await client.post('/v1/chat/completions', json={'model': 'gpt-test'})
                    assert refused.status_code == 400 and operations == ['devcore-summary']
                    assert observer.snapshot()['queued'] == 1
                    body = json.loads(calls[0][2])
                    span = body['resourceSpans'][0]['scopeSpans'][0]['spans'][0]
                    attrs = {v['key']: v['value']['stringValue'] for v in span['attributes']}
                    assert attrs['gen_ai.request.model'] == 'gemini-2.5-flash'
                    assert attrs['devcore.prompt_tokens'] == '7'
                    assert attrs['devcore.project_id'] == 'alpha'
                    assert 'private' not in str(body)
            finally:
                release.set()
                assert await worker.aclose()
        asyncio.run(scenario())


@pytest.mark.parametrize('changes', [
    {'usage': None}, {'usage': {'prompt_tokens': 7, 'completion_tokens': 3}},
    {'usage': {'prompt_tokens': True, 'completion_tokens': 3, 'total_tokens': 4}},
    {'usage': {'prompt_tokens': 7, 'completion_tokens': 3, 'total_tokens': 11}},
    {'model': 'gpt-test'}, {'choices': 'x' * 65536},
])
def test_missing_invalid_or_oversized_usage_is_not_estimated(changes):
    with pytest.raises((ValueError, TypeError)):
        adapter(response(**changes))


def test_cost_must_be_explicit_and_native_error_responses_are_refused():
    with pytest.raises(ValueError):
        adapter(response(), cost=None)
    for result in (Response('{}', status_code=500), Response('{}')):
        with pytest.raises(ValueError):
            adapter(result)


@pytest.mark.parametrize('enabled', [False, True])
def test_disabled_or_invalid_observation_preserves_response_without_retry(monkeypatch, enabled):
    with receiver() as (endpoint, calls, _, _):
        async def scenario():
            worker = OtlpWorker(exporter(endpoint))
            worker.start()
            observer = GenerationObserver(worker)
            monkeypatch.setattr(router.app.state, 'generation_observer', observer if enabled else None, raising=False)
            monkeypatch.setattr(router.app.state, 'generation_event_factory',
                (lambda request, result: adapter(result)) if enabled else None, raising=False)
            monkeypatch.setattr(router, 'check_protocol_compliance',
                lambda: type('Status', (), {'compliant': True})())
            attempts = []
            original = response(usage=None)
            async def completion(*args, **kwargs):
                attempts.append(1)
                return original
            monkeypatch.setattr(router, 'call_with_fallback', completion)
            try:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=router.app),
                    base_url='http://fixture') as client:
                    result = await client.post('/v1/chat/completions', json={'model': 'devcore-summary'})
                    assert result.content == original.body and result.status_code == original.status_code
                    assert result.headers['x-devcore-resolved-model'] == 'gemini-2.5-flash'
                    assert attempts == [1] and observer.snapshot()['errors'] == int(enabled)
                    assert worker.snapshot()['pending'] == 0
            finally:
                assert await worker.aclose()
        asyncio.run(scenario())
        assert calls == []
