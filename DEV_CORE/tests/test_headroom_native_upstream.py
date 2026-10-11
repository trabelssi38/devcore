"""Installed Headroom upstream probe using an in-memory HTTP transport only."""
import json
import httpx
import pytest
import socket


@pytest.mark.parametrize("path,model,provider", [
    ("/v1/responses", "gpt-4o", "api.openai.com"),
    ("/v1/messages", "claude-3-5-sonnet-20241022", "api.anthropic.com"),
])
def test_installed_headroom_preserves_upstream(tmp_path, monkeypatch, path, model, provider):
    pytest.importorskip("headroom", reason="Separate qualified Headroom runtime required")
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    def blocked(sock, address):
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1", "localhost"):
            return original_connect(sock, address)
        raise OSError("All real network connections are blocked in this probe")
    def blocked_ex(sock, address):
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1", "localhost"):
            return original_connect_ex(sock, address)
        raise OSError("All real network connections are blocked in this probe")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked_ex)
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("HEADROOM_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("HEADROOM_WORKSPACE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HEADROOM_STATELESS", "true")
    monkeypatch.setenv("HEADROOM_TELEMETRY", "off")
    monkeypatch.setenv("HEADROOM_SKIP_UPSTREAM_CHECK", "1")
    monkeypatch.setenv("HEADROOM_RUST_CORE_REQUIRED", "false")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    calls = []
    def fake(request):
        if request.method == "POST" and request.url.host in ("api.openai.com", "api.anthropic.com"):
            calls.append((str(request.url), json.loads(request.content)))
            if provider == "api.anthropic.com":
                result = {"id": "msg-test", "type": "message", "role": "assistant", "model": model,
                    "content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn", "usage": {"input_tokens": 2, "output_tokens": 1}}
            else:
                result = {"id": "resp-test", "object": "response", "model": model, "status": "completed", "output": [],
                    "usage": {"input_tokens": 2, "output_tokens": 1, "total_tokens": 3}}
            return httpx.Response(200, json=result)
        return httpx.Response(404, json={"error": "External calls blocked by test transport"})
    original = httpx.AsyncClient.__init__
    def isolated(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(fake)
        kwargs["trust_env"] = False
        original(self, *args, **kwargs)
    monkeypatch.setattr(httpx.AsyncClient, "__init__", isolated)
    from headroom.proxy.models import ProxyConfig
    from headroom.proxy.server import create_app
    from Scripts.headroom_routes import RouteGuard, profile
    from fastapi.testclient import TestClient
    app = RouteGuard(create_app(ProxyConfig(**profile("native"))), "native")
    body = {"model": model, "stream": False}
    if provider == "api.anthropic.com":
        body.update(messages=[{"role": "user", "content": "hello"}], max_tokens=16)
    else:
        body["input"] = "hello"
    with TestClient(app) as client:
        response = client.post(path, json=body, headers={"authorization": "Bearer fake-test-key", "x-api-key": "fake-test-key", "anthropic-version": "2023-06-01"})
    assert response.status_code == 200, response.text
    assert len(calls) == 1
    assert provider in calls[0][0]
    assert calls[0][1]["model"] == model
    assert "20130" not in calls[0][0]
