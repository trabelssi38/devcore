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

from ai_capability_registry import load_capability_registry

app = FastAPI(title="Gemini Router with Fallback")

@app.get("/health")
@app.get("/healthz")
def health_check():
    return {"status": "healthy", "service": "gemini-router", "port": 20130}

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
    body = await request.json()
    
    # === MIDDLEWARE AUTO-BOOTSTRAP ===
    status = check_protocol_compliance()
    if not status.compliant:
        body = inject_protocol_reminder(body, status)
        log_protocol_violation(status)
    # === FIN MIDDLEWARE ===
    
    headers = dict(request.headers)
    is_stream = body.get("stream", False)
    
    if not is_stream:
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
    
    return StreamingResponse(stream_generator(gemini_body, gemini_headers), media_type="text/event-stream")

@app.post("/v1/embeddings")
async def embeddings(request: Request):
    body = await request.json()
    status = check_protocol_compliance()
    if not status.compliant:
        log_protocol_violation(status)
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
        "capability_registry": load_capability_registry(),
    }

if __name__ == "__main__":
    bind_host = get_bind_host()
    print(f"Demarrage du Gemini Router sur {bind_host}:20130...")
    uvicorn.run(app, host=bind_host, port=20130)
