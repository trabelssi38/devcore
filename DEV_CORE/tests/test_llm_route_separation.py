"""Routing admission and provider preservation; no real credentials or network."""
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from Scripts.headroom_routes import RouteGuard, profile


@pytest.fixture
def router(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "CEREBRAS_API_KEY", "NVIDIA_API_KEY", "NVAPI_KEY"):
        monkeypatch.setenv(key, "test-not-a-secret")
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "Scripts"))
    for name in ("gemini_router", "anthropic_adapter", "router.config", "router.providers", "router.stream_parser"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    module = importlib.import_module("gemini_router")
    providers = importlib.import_module("router.providers")
    return module, providers, tmp_path


@pytest.mark.parametrize("model", ["gpt-4o", "gpt-6-codex", "codex-mini", "claude-3-5-sonnet", "devcore-coding", "devcore-reasoning", "gemini-unknown", None])
@pytest.mark.parametrize("stream", [False, True])
def test_router_refuses_before_side_effects(router, monkeypatch, model, stream):
    module, providers, root = router
    def forbidden(*args, **kwargs):
        pytest.fail("Rejected routing must not touch protocol state or network")
    monkeypatch.setattr(module, "check_protocol_compliance", forbidden)
    monkeypatch.setattr(providers.client, "post", forbidden)
    with TestClient(module.app) as client:
        response = client.post("/v1/chat/completions", json={"model": model, "stream": stream, "messages": []})
    assert response.status_code == 400
    assert not (root / "data").exists()


def test_embeddings_refuse_native_and_preserve_content(router, monkeypatch):
    module, providers, root = router
    monkeypatch.setattr(module, "check_protocol_compliance", lambda: pytest.fail("No protocol access on refusal"))
    with TestClient(module.app) as client:
        assert client.post("/v1/embeddings", json={"model": "text-embedding-3-small", "input": "hello"}).status_code == 400
    body = {"model": "gemini-embedding-001", "input": ["hello", "world"], "dimensions": 768}
    assert providers.map_for_gemini(body, False) == body
    assert not (root / "data").exists()


@pytest.mark.parametrize('path', ['/v1/chat/completions', '/v1/embeddings', '/v1/messages'])
@pytest.mark.parametrize('raw,status', [(b'[' * 1500 + b']' * 1500, 400),
    (b'\xff', 400), (b' ' * (16 * 1024 * 1024 + 1), 413)], ids=['deep-json', 'invalid-utf8', 'oversized'])
def test_auxiliary_body_refused_before_state_and_provider(router, monkeypatch, path, raw, status):
    module, providers, root = router
    def forbidden(*args, **kwargs):
        pytest.fail('Invalid body reached state or provider')
    monkeypatch.setattr(module, 'check_protocol_compliance', forbidden)
    monkeypatch.setattr(providers.client, 'post', forbidden)
    app = module.app
    if path == '/v1/messages':
        adapter = importlib.import_module('anthropic_adapter')
        monkeypatch.setattr(adapter.client, 'post', forbidden)
        app = adapter.app
    with TestClient(app) as client:
        response = client.post(path, content=raw, headers={'content-type': 'application/json'})
    assert response.status_code == status
    assert response.json()['error']['type'] == 'routing_policy_error'
    assert len(response.content) < 256
    assert not (root / 'data').exists()


@pytest.mark.parametrize('adapter_profile', [False, True])
def test_actual_auxiliary_application_bounds_eight_inflight_bodies(router, monkeypatch, adapter_profile):
    import asyncio
    module, providers, root = router
    def forbidden(*args, **kwargs):
        pytest.fail('Refused request touched state/provider')
    monkeypatch.setattr(module, 'check_protocol_compliance', forbidden)
    monkeypatch.setattr(providers.client, 'post', forbidden)
    path = '/v1/chat/completions'
    if adapter_profile:
        module = importlib.import_module('anthropic_adapter')
        monkeypatch.setattr(module.client, 'post', forbidden)
        path = '/v1/messages'
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        count = 0
        async def slow_body(request):
            nonlocal count
            count += 1
            if count == 8:
                entered.set()
            await release.wait()
            return {}  # Policy refusal after admission, never a provider call.
        monkeypatch.setattr(module, 'read_json_body', slow_body)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=module.app), base_url='http://fixture', trust_env=False) as client:
            tasks = [asyncio.create_task(client.post(path, content=b'{}')) for _ in range(8)]
            try:
                await asyncio.wait_for(entered.wait(), 2)
                refused = await asyncio.wait_for(client.post(path, content=b'{}'), .5)
                assert refused.status_code == 503 and count == 8
                assert refused.json()['error']['type'] == 'service_capacity_exceeded'
                metrics = await asyncio.wait_for(client.get('/devcore/admission'), .5)
                assert metrics.status_code == 200
                assert metrics.json()['active'] == metrics.json()['admitted'] == 8
                assert metrics.json()['rejected_http'] == 1
                health = await asyncio.wait_for(client.get('/health'), .5)
                assert health.status_code == (404 if adapter_profile else 200)
                assert all(not task.done() for task in tasks)
            finally:
                release.set()
                responses = await asyncio.wait_for(asyncio.gather(*tasks), 2)
            assert all(response.status_code == 400 for response in responses)
            assert (await client.post(path, content=b'{}')).status_code == 400
            metrics = (await client.get('/devcore/admission')).json()
            assert metrics['active'] == 0 and metrics['finished'] == 9
    asyncio.run(scenario())
    assert not (root / 'data').exists()


@pytest.mark.parametrize('route,path', [('native', '/v1/responses'),
    ('native', '/v1/messages'), ('auxiliary', '/v1/chat/completions')])
def test_headroom_deep_json_refused_without_upstream(route, path):
    async def forbidden(scope, receive, send):
        if scope['type'] == 'lifespan':
            while True:
                event = await receive()
                await send({'type': event['type'] + '.complete'})
                if event['type'] == 'lifespan.shutdown':
                    return
        pytest.fail('Malformed input reached upstream')
    with TestClient(RouteGuard(forbidden, route)) as client:
        response = client.post(path, content=b'[' * 65 + b']' * 65)
    assert response.status_code == 400
    assert response.json()['error']['message'] == 'Invalid JSON or excessive nesting'


@pytest.mark.parametrize("alias", ["devcore-writing", "devcore-documentation", "devcore-summary", "devcore-bulk"])
def test_auxiliary_alias_has_fixed_resolution(router, alias):
    _, providers, _ = router
    mapped = providers.map_for_gemini({"model": alias, "messages": [], "capability_requirements": {"model": "gpt-4o"}, "fallback_providers": ["cerebras"]}, True)
    assert mapped == {"model": "gemini-2.5-flash", "messages": []}


@pytest.mark.parametrize("authorized", [False, True])
def test_fallback_requires_explicit_request(router, monkeypatch, authorized):
    _, providers, _ = router
    monkeypatch.setattr(providers, "API_KEY", "")
    monkeypatch.setattr(providers, "NVIDIA_API_KEY", "")
    monkeypatch.setattr(providers, "get_active_task_and_mode", lambda: ("T-test", "bulk"))
    monkeypatch.setattr(providers, "record_tokens", lambda *args: None)
    monkeypatch.setattr(providers, "has_budget_alert", lambda *args: False)
    calls = []
    async def post(url, *, json, headers):
        calls.append((url, json))
        return httpx.Response(200, json={"choices": [], "usage": {"prompt_tokens": 2}}, request=httpx.Request("POST", url))
    async def reader(client, url, *, json, headers):
        return await post(url, json=json, headers=headers)
    monkeypatch.setattr(providers, "post_bounded", reader)
    body = {"model": "devcore-bulk", "messages": []}
    if authorized:
        body["fallback_providers"] = ["cerebras"]
    import asyncio
    response = asyncio.run(providers.call_with_fallback("chat/completions", body, {}, True))
    assert len(calls) == int(authorized)
    if authorized:
        assert calls[0][1] == {"model": "llama-3.3-70b", "messages": []}
        assert response.headers["x-devcore-requested-model"] == "devcore-bulk"
        assert response.headers["x-devcore-resolved-model"] == "llama-3.3-70b"
        assert response.headers["x-devcore-route"] == "auxiliary"


def guarded(route):
    app = FastAPI()
    @app.post("/{path:path}")
    async def echo(request: Request):
        return await request.json()
    return RouteGuard(app, route)


@pytest.mark.parametrize("path,model", [("/v1/responses", "gpt-6-codex"), ("/v1/messages", "claude-sonnet-4-6"), ("/v1/chat/completions", "gpt-4o")])
def test_native_preserves_model_and_provider(path, model):
    app = guarded("native")
    body = {"model": model, "messages": [{"role": "user", "content": "unchanged"}], "stream": False}
    with TestClient(app) as client:
        response = client.post(path, json=body)
        assert response.json() == body
        assert response.headers["x-devcore-resolved-model"] == model
        metrics = client.get("/devcore/routes").json()["recent_requests"]
        assert metrics[-1]["requested_model"] == metrics[-1]["resolved_model"]
        assert metrics[-1]["requested_provider"] == metrics[-1]["upstream_provider"]
        assert metrics[-1]["provider"] == ("anthropic" if path == "/v1/messages" else "openai")


@pytest.mark.parametrize("route,path,body,headers", [
    ("native", "/v1/responses", {"model": "devcore-bulk"}, {}),
    ("native", "/v1/messages", {"model": "gpt-4o"}, {}),
    ("native", "/v1/responses", {"model": "gpt-4o"}, {"x-headroom-base-url": "http://127.0.0.1:20130"}),
    ("native", "/v1/responses", {"model": "gpt-4o", "provider": "gemini"}, {}),
    ("auxiliary", "/v1/messages", {"model": "devcore-bulk"}, {}),
    ("auxiliary", "/v1/responses", {"model": "gpt-4o"}, {}),
    ("auxiliary", "/v1/embeddings", {"model": "gemini-embedding-001"}, {}),
    ("auxiliary", "/v1/chat/completions", {"model": "claude-test"}, {}),
    ("native", "/api/settings", {"openai_api_url": "http://127.0.0.1:20130"}, {}),
])
def test_closed_headroom_surface(route, path, body, headers):
    with TestClient(guarded(route)) as client:
        assert client.post(path, json=body, headers=headers).status_code in (400, 404)


def test_profiles_are_distinct_and_ignore_global_routing(monkeypatch):
    monkeypatch.setenv("OPENAI_TARGET_API_URL", "http://127.0.0.1:20130/v1")
    native, auxiliary = profile("native"), profile("auxiliary")
    assert native["port"] == 8787 and auxiliary["port"] == 8789
    assert native["openai_api_url"] == "https://api.openai.com"
    assert native["anthropic_api_url"] == "https://api.anthropic.com"
    assert native["model_router"] is None
    assert auxiliary["openai_api_url"] == "http://127.0.0.1:20130"


def test_auxiliary_adapter_rejects_native_before_network(router, monkeypatch):
    adapter = importlib.import_module("anthropic_adapter")
    monkeypatch.setattr(adapter.client, "post", lambda *a, **kw: pytest.fail("No native translation"))
    assert adapter.HEADROOM_URL == "http://127.0.0.1:8789/v1"
    with TestClient(adapter.app) as client:
        assert client.post("/v1/messages", json={"model": "claude-sonnet-4-6", "messages": []}).status_code == 400


def test_workflow_profiles_preserve_native_model(router, monkeypatch):
    dc = importlib.import_module("Scripts.dc")
    for mode in ("coding", "reasoning", "plan"):
        value = dc.resolve_routing_profile(mode)
        assert value["route"] == "native"
        assert value["model"] is None and value["gemini_model"] is None
    bulk = dc.resolve_routing_profile("bulk")
    assert bulk["route"] == "auxiliary" and bulk["model"] == "devcore-bulk"
    with pytest.raises(ValueError):
        dc.resolve_routing_profile("unknown")


@pytest.mark.parametrize("body", [{"model": "devcore-bulk", "fallback_providers": "cerebras"},
    {"model": "devcore-bulk", "stream": True, "fallback_providers": ["cerebras"]},
    {"model": "devcore-bulk", "fallback_providers": ["unknown"]}])
def test_invalid_fallback_never_reaches_network(router, monkeypatch, body):
    module, _, _ = router
    monkeypatch.setattr(module, "check_protocol_compliance", lambda: pytest.fail("No protocol access"))
    with TestClient(module.app) as client:
        assert client.post("/v1/chat/completions", json=body).status_code == 400
