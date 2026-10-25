"""Authenticated Gemini usage is attributable and contains no prompt in storage."""

import asyncio
from pathlib import Path
import sys

import httpx
import pytest


API_ROOT = Path(__file__).resolve().parents[1] / "API"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from devcore_api.team_gemini import GeminiRouteUnavailable, generate_project_summary
from devcore_api.app import create_app
from devcore_engine.security.identity import Principal, ProjectAccessDenied
from fastapi.testclient import TestClient


class UsageStore:
    def __init__(self):
        self.records = []

    def record_gemini(self, principal, **values):
        self.records.append((principal, values))
        return True


def _client(*, provider="google-gemini"):
    def reply(request):
        assert request.url.host == "127.0.0.1"
        return httpx.Response(200, json={"model": "gemini-2.5-flash", "choices": [
            {"message": {"content": "Résumé."}}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 3}},
            headers={"x-devcore-route": "auxiliary", "x-devcore-provider": provider,
                     "x-devcore-resolved-model": "gemini-2.5-flash"})
    return httpx.AsyncClient(transport=httpx.MockTransport(reply))


def test_authenticated_gemini_call_records_only_provider_usage():
    async def run():
        principal = Principal("alice", "credential", "alpha", "task.mutate")
        store = UsageStore()
        async with _client() as client:
            result = await generate_project_summary(
                principal, "Secret prompt for this request", store, client=client)
        assert result["project"] == "alpha"
        assert result["content"] == "Résumé."
        assert result["usage"] == {"prompt_tokens": 7,
                                   "completion_tokens": 3,
                                   "source": "provider_reported"}
        assert store.records[0][1]["prompt_tokens"] == 7
        assert "Secret prompt" not in repr(store.records)
    asyncio.run(run())


def test_gemini_call_rejects_wrong_provider_and_read_only_principal():
    async def run():
        store = UsageStore()
        async with _client(provider="another-provider") as client:
            with pytest.raises(GeminiRouteUnavailable):
                await generate_project_summary(
                    Principal("alice", "credential", "alpha", "task.mutate"),
                    "Prompt", store, client=client)
            with pytest.raises(ProjectAccessDenied):
                await generate_project_summary(
                    Principal("alice", "credential", "alpha", "task.read"),
                    "Prompt", store, client=client)
        assert store.records == []
    asyncio.run(run())


def test_gateway_rejects_anonymous_gemini_request_before_upstream():
    app = create_app(require_auth=True, start_run_worker=False)
    with TestClient(app) as client:
        response = client.post("/api/v1/llm/gemini", json={
            "project": "alpha", "prompt": "No credential"})
    assert response.status_code == 401
