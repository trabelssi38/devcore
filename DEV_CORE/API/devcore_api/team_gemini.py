"""Authenticated, bounded Gemini call with durable project attribution."""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import httpx

from devcore_engine.security.identity import Principal, ProjectAccessDenied
from devcore_engine.services.postgres_llm_usage import PostgresLlmUsageStore


UPSTREAM = "http://127.0.0.1:8789/v1/chat/completions"


class GeminiRouteUnavailable(RuntimeError):
    pass


async def generate_project_summary(
    principal: Principal, prompt: str, usage_store: PostgresLlmUsageStore,
    *, client: httpx.AsyncClient | None = None,
) -> dict:
    if not isinstance(principal, Principal) or principal.action != "task.mutate":
        raise ProjectAccessDenied("Project mutation principal required")
    if not isinstance(prompt, str) or not 1 <= len(prompt) <= 4096 or not prompt.strip():
        raise ValueError("Prompt must contain 1–4096 characters")
    body = {"model": "devcore-summary", "messages": [
        {"role": "user", "content": prompt}], "max_tokens": 256, "stream": False}
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=120, trust_env=False)
    try:
        response = await client.post(UPSTREAM, json=body)
    except (httpx.HTTPError, TimeoutError) as exc:
        raise GeminiRouteUnavailable("Gemini route unavailable") from exc
    finally:
        if own_client:
            await client.aclose()
    if (response.status_code != 200 or len(response.content) > 65536
            or response.headers.get("x-devcore-route") != "auxiliary"
            or response.headers.get("x-devcore-provider") != "google-gemini"):
        raise GeminiRouteUnavailable("Gemini route did not return a qualified response")
    try:
        payload = json.loads(response.content)
        model = response.headers["x-devcore-resolved-model"]
        if payload["model"] != model or not isinstance(model, str) or len(model) > 128:
            raise ValueError("Model mismatch")
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str) or len(content) > 16384:
            raise ValueError("Invalid response text")
        usage = payload.get("usage")
        if usage is None:
            prompt_tokens = completion_tokens = None
        else:
            prompt_tokens = usage["prompt_tokens"]
            completion_tokens = usage["completion_tokens"]
        trace_id = str(uuid4())
        inserted = await asyncio.to_thread(
            usage_store.record_gemini, principal, trace_id=trace_id, model=model,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
        if not inserted:
            raise RuntimeError("Unexpected duplicate Gemini trace")
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise GeminiRouteUnavailable("Gemini response could not be attributed") from exc
    return {"project": principal.project_id, "trace_id": trace_id,
            "provider": "google-gemini", "model": model, "content": content,
            "usage": {"prompt_tokens": prompt_tokens,
                      "completion_tokens": completion_tokens,
                      "source": "provider_reported" if usage is not None else "unreported"}}
