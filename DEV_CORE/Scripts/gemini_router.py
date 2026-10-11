# gemini_router.py -- DEV_CORE v10.0
# Léger proxy de complétion pour utiliser Gemini en direct par defaut
# Port : 20130 (Amont de Headroom Proxy)

import os
import sys
import json
import uvicorn
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

# Add parent directory to path so we can import from router package
sys.path.append(str(Path(__file__).resolve().parent))

from router.config import (
    MODEL_MAP,
    MODE_MODEL_MAP,
    API_KEY,
    PUBLIC_BIND_HOSTS,
    NETWORK_CONFIG_PATH,
    DEV_CORE
)

from router.providers import (
    check_protocol_compliance,
    inject_protocol_reminder,
    log_protocol_violation,
    map_for_gemini,
    call_with_fallback
)

from router.stream_parser import stream_generator

from router.policy import validate_auxiliary, route_headers, TASK_TYPES
from router.request_body import read_json_body, BodyRefusal
from router.admission import AdmissionGuard
from router.observation import observation_lifespan
from router import providers as provider_state
from router.rate_limit import RateLimitRefusal

app = FastAPI(title="Gemini Router with Fallback", lifespan=observation_lifespan)
app.add_middleware(AdmissionGuard, max_requests=8)

@app.get("/health")
@app.get("/healthz")
def health_check():
    return {"status": "healthy", "service": "gemini-router", "port": 20130,
            "route": "auxiliary", "policy_version": 2}

def read_network_config() -> dict:
    if not NETWORK_CONFIG_PATH.exists():
        return {}
    try:
        with open(NETWORK_CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[GeminiRouter] Unable to read network config {NETWORK_CONFIG_PATH}: {exc}")
        return {}

def get_bind_host() -> str:
    host = os.environ.get("DEVCORE_GEMINI_ROUTER_BIND", "").strip()
    if not host:
        config = read_network_config()
        host = (
            config.get("services", {})
            .get("gemini_router", {})
            .get("host")
            or config.get("default_bind_host")
            or "127.0.0.1"
        )
    host = str(host).strip()
    if host in PUBLIC_BIND_HOSTS and os.environ.get("DEVCORE_ALLOW_PUBLIC_BIND") != "1":
        raise ValueError("Public bind requires DEVCORE_ALLOW_PUBLIC_BIND=1")
    return host or "127.0.0.1"

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        body = await read_json_body(request)
        validate_auxiliary(body, is_chat=request.url.path != "/v1/embeddings")
    except ValueError as exc:
        return Response(content=json.dumps({"error": {"type": "routing_policy_error", "message": str(exc)}}), status_code=exc.status if isinstance(exc, BodyRefusal) else 400, media_type="application/json")
    
    headers = dict(request.headers)
    is_stream = body.get("stream", False)
    
    if not is_stream:
        observer = getattr(request.app.state, 'generation_observer', None)
        factory = getattr(request.app.state, 'generation_event_factory', None)
        if observer is not None and factory is not None:
            return await observer.run(
                lambda: call_with_fallback("chat/completions", body, headers, is_chat=True),
                event_from_result=lambda result: factory(request, result))
        return await call_with_fallback("chat/completions", body, headers, is_chat=True)
        
    # Streaming route
    gemini_body = map_for_gemini(body, is_chat=True)
    if not API_KEY:
        async def missing_key_generator():
            yield json.dumps({
                "error": {
                    "message": "GEMINI_API_KEY or GEMINI_API_KEY_FILE is required",
                    "type": "configuration_error"
                }
            }).encode("utf-8")

        return StreamingResponse(
            missing_key_generator(),
            status_code=503,
            media_type="text/event-stream"
        )

    gemini_headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        estimated_tokens = max(100, len(json.dumps(gemini_body.get('messages', []))) // 4)
        await provider_state.rate_limiter.wait_if_needed(estimated_tokens)
    except RateLimitRefusal as exc:
        return Response(content=json.dumps({'error': {'type': 'local_rate_limit',
            'message': 'Local provider admission saturated'}}), status_code=429,
            media_type='application/json', headers={'Retry-After': str(exc.retry_after)})
    
    return StreamingResponse(stream_generator(gemini_body, gemini_headers, limiter=provider_state.rate_limiter,
        estimated_tokens=estimated_tokens, accounting_mode=TASK_TYPES[body['model']]), media_type="text/event-stream",
        headers={**route_headers(body, gemini_body["model"], "google-gemini"), "X-DevCore-Attribution": "unattributed"})

@app.post("/v1/embeddings")
async def embeddings(request: Request):
    try:
        body = await read_json_body(request)
        validate_auxiliary(body, is_chat=request.url.path != "/v1/embeddings")
    except ValueError as exc:
        return Response(content=json.dumps({"error": {"type": "routing_policy_error", "message": str(exc)}}), status_code=exc.status if isinstance(exc, BodyRefusal) else 400, media_type="application/json")
    headers = dict(request.headers)
    return await call_with_fallback("embeddings", body, headers, is_chat=False)

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": k, "object": "model", "owned_by": "gemini-router"} for k in MODEL_MAP.keys()
        ]
    }

@app.get("/v1/devcore/routing-profiles")
async def routing_profiles():
    return {
        "object": "devcore.routing_profiles",
        "modes": MODE_MODEL_MAP,
        "models": MODEL_MAP,
        "route": "auxiliary",
        "fallback": "explicit fallback_providers list; non-streaming only",
    }

if __name__ == "__main__":
    bind_host = get_bind_host()
    print(f"Demarrage du Gemini Router sur {bind_host}:20130...")
    from service_runtime import run_managed
    run_managed(app, host=bind_host, port=20130, service='router')
