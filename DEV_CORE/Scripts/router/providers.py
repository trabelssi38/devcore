import sys
import json
import asyncio
import datetime
from dataclasses import dataclass
import httpx
from fastapi import Response

from .policy import validate_auxiliary, strip_controls, route_headers, EMBEDDING_MODEL, TASK_TYPES
from .usage import reported_usage
from .stats_store import update_stats, read_stats
from .request_body import decode_json_async, BodyRefusal
from .upstream_body import post_bounded, UpstreamBodyRefusal
from .rate_limit import SlidingWindowRateLimiter, RateLimitRefusal
from .config import (
    DEV_CORE,
    DEV_CORE_DATA,
    API_KEY,
    CEREBRAS_API_KEY,
    NVIDIA_API_KEY,
    MODEL_MAP,
    MODE_MODEL_MAP,
    BUDGET_THRESHOLDS,
    GEMINI_BASE_URL,
    ALERTS_LOG,
    STATS_PATH,
)

# Async HTTP Client with timeouts for long contexts
client = httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0))

rate_limiter = SlidingWindowRateLimiter()
fallback_limiters = {
    'cerebras': SlidingWindowRateLimiter(),
    'nvidia-nim': SlidingWindowRateLimiter(),
}

def get_active_task_and_mode() -> tuple:
    raise RuntimeError("Shared active task lookup is retired; use request-scoped attribution")

def check_and_trigger_alerts(task_id: str, mode: str, total_tokens: int):
    threshold = BUDGET_THRESHOLDS.get(mode, 1000000)
    if total_tokens > threshold:
        alert_msg = f"[DEV_CORE BUDGET ALERT] Task {task_id} ({mode} mode) has consumed {total_tokens} tokens, exceeding budget of {threshold}."
        print(alert_msg)
        
        try:
            ALERTS_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(ALERTS_LOG, "a", encoding="utf-8") as f:
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{ts}] {alert_msg}\n")
        except Exception:
            print("[GeminiRouter] Alert log write failed", file=sys.stderr)

def record_tokens(task_id: str, mode: str, prompt_tokens: int, completion_tokens: int):
    try:
        total = update_stats(STATS_PATH, task_id, mode, prompt_tokens, completion_tokens)
    except (OSError, ValueError):
        print('[GeminiRouter] Usage snapshot update refused', file=sys.stderr)
        return False
    # A failed alert after commit must never repeat the usage update.
    try:
        check_and_trigger_alerts(task_id, mode, total)
    except Exception:
        print('[GeminiRouter] Usage alert failed', file=sys.stderr)
    return True


def has_budget_alert(task_id: str) -> bool:
    try:
        task = read_stats(STATS_PATH)['tasks'].get(task_id)
        if task:
            return task['total_tokens'] > BUDGET_THRESHOLDS.get(task['mode'], 1000000)
    except (OSError, ValueError):
        pass
    return False

@dataclass
class ProtocolStatus:
    compliant: bool
    task_id: str
    mode: str
    ephemeral: bool
    violation_count: int

def check_protocol_compliance() -> ProtocolStatus:
    raise RuntimeError("Shared protocol state is retired; use request-scoped attribution")

def inject_protocol_reminder(body: dict, status: ProtocolStatus) -> dict:
    raise RuntimeError("Shared protocol reminder is retired")

def log_protocol_violation(status: ProtocolStatus):
    raise RuntimeError("Shared protocol log is retired")

def map_for_gemini(body: dict, is_chat: bool) -> dict:
    model = validate_auxiliary(body, is_chat=is_chat)
    mapped = strip_controls(body)
    mapped["model"] = MODEL_MAP[model] if is_chat else EMBEDDING_MODEL
    return mapped

def auxiliary_accounting(body, *, is_chat=True):
    model = validate_auxiliary(body, is_chat=is_chat)
    mode = TASK_TYPES.get(model, 'embedding')
    return 'unattributed.' + mode, mode


async def _try_provider_request(url: str, body: dict, api_key: str, provider_name: str, requested_body: dict) -> Response | None:
    """Execute request to an OpenAI-compatible provider with standard response building."""
    limiter = fallback_limiters[provider_name]
    estimated_tokens = max(100, len(json.dumps(body.get('messages', []))) // 4)
    await limiter.wait_if_needed(estimated_tokens)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    r = await post_bounded(client, url, json=body, headers=headers)
    if r.status_code == 200:
        resp_json = await decode_provider_json(r.content)
        task_id, mode = auxiliary_accounting(requested_body)
        usage_source = 'unavailable'
        try:
            usage = reported_usage(resp_json)
            if usage is not None:
                usage_source = 'provider_reported'
                p_tok, c_tok = usage
                await limiter.record_tokens(p_tok + c_tok)
                record_tokens(task_id, mode, p_tok, c_tok)
        except Exception:
            pass
        out_headers = {"Content-Type": "application/json", "X-DevCore-Task": task_id, "X-DevCore-Provider": provider_name}
        out_headers['X-DevCore-Usage-Source'] = usage_source
        out_headers['X-DevCore-Attribution'] = 'unattributed'
        out_headers.update(route_headers(requested_body, body["model"], provider_name))
        if has_budget_alert(task_id):
            out_headers["X-DevCore-Budget-Alert"] = "True"
        return Response(content=r.content, status_code=200, headers=out_headers)
    else:
        print(f"[GeminiRouter] Provider {provider_name} returned status {r.status_code}")
        return None

async def decode_provider_json(raw):
    """Validate bounded provider JSON before usage parsing or success forwarding."""
    if len(raw) > 16 * 1024 * 1024:
        raise UpstreamBodyRefusal('Provider JSON exceeds byte capacity')
    try:
        payload = await decode_json_async(raw)
    except BodyRefusal as exc:
        raise UpstreamBodyRefusal('Invalid provider JSON or excessive nesting') from exc
    if not isinstance(payload, dict):
        raise UpstreamBodyRefusal('Provider JSON must be an object')
    return payload


async def call_with_fallback(path: str, body: dict, headers: dict, is_chat: bool, *, deadline_seconds=120.0) -> Response:
    """One cooperative deadline for admission, upstream calls and backoffs."""
    if type(deadline_seconds) not in (int, float) or not 0 < deadline_seconds <= 120:
        raise ValueError('Request deadline must be positive and at most 120 seconds')
    try:
        async with asyncio.timeout(deadline_seconds):
            return await _call_with_fallback(path, body, headers, is_chat)
    except UpstreamBodyRefusal:
        return Response(content=json.dumps({'error': {'type': 'provider_response_refused',
            'message': 'Provider response exceeds allowed transport bounds'}}), status_code=502,
            media_type='application/json')
    except TimeoutError:
        return Response(content=json.dumps({'error': {'type': 'provider_deadline',
            'message': 'Provider request deadline exceeded'}}), status_code=504,
            media_type='application/json')


async def _call_with_fallback(path: str, body: dict, headers: dict, is_chat: bool) -> Response:
    validate_auxiliary(body, is_chat=is_chat)
    permitted = body.get("fallback_providers", [])
    if not API_KEY and not CEREBRAS_API_KEY and not NVIDIA_API_KEY:
        return Response(
            content=json.dumps({
                "error": {
                    "message": "No API keys configured (GEMINI_API_KEY, CEREBRAS_API_KEY, or NVIDIA_API_KEY)",
                    "type": "configuration_error"
                }
            }),
            status_code=503,
            media_type="application/json"
        )

    messages = body.get("messages", [])
    est_tokens = max(100, len(json.dumps(messages)) // 4) if is_chat else 50

    # 1. Google Gemini
    if API_KEY:
        retries = 3
        delay = 1.0
        for attempt in range(retries):
            try:
                await rate_limiter.wait_if_needed(est_tokens)
                gemini_body = map_for_gemini(body, is_chat)
                gemini_headers = {
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                }
                url = f"{GEMINI_BASE_URL}/{path}"
                r = await post_bounded(client, url, json=gemini_body, headers=gemini_headers)

                if r.status_code == 429:
                    retry_after = r.headers.get("Retry-After")
                    wait_time = float(retry_after) if retry_after and retry_after.isdigit() else delay
                    print(f"[GeminiRouter] Gemini 429 Rate limit (essai {attempt+1}/{retries}). Attente {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    delay *= 2
                    continue
                elif r.status_code >= 500:
                    print(f"[GeminiRouter] Gemini Erreur serveur ({r.status_code}) (essai {attempt+1}/{retries}). Attente {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue

                r.raise_for_status()
                resp_content = r.content
                resp_json = await decode_provider_json(resp_content)
                task_id, mode = auxiliary_accounting(body, is_chat=is_chat)
                usage_source = 'unavailable'
                try:
                    usage = reported_usage(resp_json, is_chat=is_chat)
                    if usage is not None:
                        usage_source = 'provider_reported'
                        p_tokens, c_tokens = usage
                        tot_tokens = p_tokens + c_tokens
                        record_tokens(task_id, mode, p_tokens, c_tokens)
                        await rate_limiter.record_tokens(tot_tokens)
                except Exception:
                    print("[GeminiRouter] Token recording failed")

                headers_out = {
                    "Content-Type": "application/json",
                    "X-DevCore-Task": task_id,
                    "X-DevCore-Provider": "google-gemini"
                }
                headers_out.update(route_headers(body, gemini_body["model"], "google-gemini", is_chat=is_chat))
                headers_out['X-DevCore-Usage-Source'] = usage_source
                headers_out['X-DevCore-Attribution'] = 'unattributed'
                if has_budget_alert(task_id):
                    headers_out["X-DevCore-Budget-Alert"] = "True"

                return Response(content=resp_content, status_code=r.status_code, headers=headers_out)
            except UpstreamBodyRefusal:
                raise
            except RateLimitRefusal as exc:
                return Response(content=json.dumps({'error': {'type': 'local_rate_limit',
                    'message': 'Local provider admission saturated'}}), status_code=429,
                    media_type='application/json', headers={'Retry-After': str(exc.retry_after)})
            except Exception:
                print(f"[GeminiRouter] Gemini call attempt {attempt+1}/{retries} failed")
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2

    # 2. Fallback: Cerebras
    if CEREBRAS_API_KEY and is_chat and "cerebras" in permitted:
        print("[GeminiRouter] Bascule automatique vers le provider de secours #1 : Cerebras (llama-3.3-70b)...")
        try:
            cerebras_body = strip_controls(body)
            cerebras_body["model"] = "llama-3.3-70b"
            for k in ("mode", "workflow_step", "capability_requirements", "requirements"):
                cerebras_body.pop(k, None)
            res = await _try_provider_request("https://api.cerebras.ai/v1/chat/completions", cerebras_body, CEREBRAS_API_KEY, "cerebras", body)
            if res:
                return res
        except UpstreamBodyRefusal:
            raise
        except RateLimitRefusal as exc:
            return Response(content=json.dumps({'error': {'type': 'local_rate_limit',
                'message': 'Local provider admission saturated'}}), status_code=429,
                media_type='application/json', headers={'Retry-After': str(exc.retry_after)})
        except Exception:
            print("[GeminiRouter] Cerebras fallback failed")

    # 3. Fallback: NVIDIA NIM
    if NVIDIA_API_KEY and is_chat and "nvidia" in permitted:
        print("[GeminiRouter] Bascule automatique vers le provider de secours #2 : NVIDIA NIM (meta/llama-3.3-70b-instruct)...")
        try:
            nvidia_body = strip_controls(body)
            nvidia_body["model"] = "meta/llama-3.3-70b-instruct"
            for k in ("mode", "workflow_step", "capability_requirements", "requirements"):
                nvidia_body.pop(k, None)
            res = await _try_provider_request("https://integrate.api.nvidia.com/v1/chat/completions", nvidia_body, NVIDIA_API_KEY, "nvidia-nim", body)
            if res:
                return res
        except UpstreamBodyRefusal:
            raise
        except RateLimitRefusal as exc:
            return Response(content=json.dumps({'error': {'type': 'local_rate_limit',
                'message': 'Local provider admission saturated'}}), status_code=429,
                media_type='application/json', headers={'Retry-After': str(exc.retry_after)})
        except Exception:
            print("[GeminiRouter] NVIDIA NIM fallback failed")

    error_msg = "All completion providers (Gemini, Cerebras, NVIDIA NIM) failed or returned errors."
    print(f"[GeminiRouter] {error_msg}")
    return Response(
        content=json.dumps({"error": {"message": error_msg, "type": "multi_provider_error"}}),
        status_code=502,
        media_type="application/json"
    )
