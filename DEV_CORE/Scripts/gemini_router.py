# gemini_router.py -- DEV_CORE v9.0
# Léger proxy de complétion pour utiliser Gemini en direct par defaut
# Port : 20130 (Amont de Headroom Proxy)

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx
import os
import json
import asyncio

app = FastAPI(title="Gemini Router with Fallback")

DEV_CORE = os.environ.get("DEVCORE_PLATFORM_ROOT", "C:\\devcore\\DEV_CORE")
DEV_CORE_DATA = os.environ.get("DEVCORE_DATA_ROOT", "C:\\devcore\\DEV_CORE_DATA")
KEY_PATH = os.path.join(DEV_CORE, "Config", "gemini_api_key.txt")

# Charger la clé API
if os.path.exists(KEY_PATH):
    with open(KEY_PATH, "r", encoding="utf-8") as f:
        API_KEY = f.read().strip()
else:
    API_KEY = "AQ.Ab8RN6Le1duZfe6u_nI0ur6PXxzms8pFrEmbZlvmfoJ56ury2A" # Fallback key

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/v1"

# Client HTTP asynchrone
client = httpx.AsyncClient(timeout=60.0)

# Mappage des modèles pour combler les exigences de DevCore
MODEL_MAP = {
    "claude-3-5-sonnet": "gemini-2.5-pro",
    "claude-3-5-sonnet-20241022": "gemini-2.5-pro",
    "claude-3-opus": "gemini-2.5-pro",
    "claude-3-haiku": "gemini-2.5-flash",
    "gpt-4o": "gemini-2.5-pro",
    "gpt-4o-mini": "gemini-2.5-flash",
    "devcore-always-on": "gemini-2.5-pro"
}

def map_for_gemini(body: dict, is_chat: bool) -> dict:
    mapped = body.copy()
    if is_chat:
        original_model = body.get("model", "devcore-always-on")
        mapped["model"] = MODEL_MAP.get(original_model, "gemini-2.5-flash")
        # Supprimer max_tokens si trop petit pour éviter les erreurs Gemini
        if "max_tokens" in mapped and mapped["max_tokens"] < 50:
            del mapped["max_tokens"]
    else:
        mapped["model"] = "gemini-embedding-001"
    return mapped

async def call_with_fallback(path: str, body: dict, headers: dict, is_chat: bool) -> Response:
    retries = 3
    delay = 1.0
    
    # Tenter l'appel direct vers Google Gemini avec Rate-Limiting retries
    last_error = None
    for attempt in range(retries):
        try:
            gemini_body = map_for_gemini(body, is_chat)
            gemini_headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
            url = f"{GEMINI_BASE_URL}/{path}"
            r = await client.post(url, json=gemini_body, headers=gemini_headers)
            
            if r.status_code == 429:
                print(f"[GeminiRouter] Rate limit (429) sur essai {attempt+1}/{retries}. Attente {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2
                continue
            elif r.status_code >= 500:
                print(f"[GeminiRouter] Erreur serveur ({r.status_code}) sur essai {attempt+1}/{retries}. Attente {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2
                continue
                
            r.raise_for_status()
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
        except Exception as e:
            last_error = e
            print(f"[GeminiRouter] Echec appel direct Gemini (essai {attempt+1}/{retries}) : {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
            
    # Echec critique sans fallback
    print(f"[GeminiRouter] Tous les essais directs Gemini ont echoue.")
    error_msg = f"Gemini API call failed after {retries} retries. Error: {last_error}"
    return Response(
        content=json.dumps({"error": {"message": error_msg, "type": "gemini_error"}}),
        status_code=502,
        media_type="application/json"
    )

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    headers = dict(request.headers)
    is_stream = body.get("stream", False)
    
    if not is_stream:
        return await call_with_fallback("chat/completions", body, headers, is_chat=True)
        
    # Streaming avec retries et fallback
    gemini_body = map_for_gemini(body, is_chat=True)
    gemini_headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    async def stream_generator():
        success = False
        retries = 3
        delay = 1.0
        last_error = None
        
        for attempt in range(retries):
            try:
                async with client.stream(
                    "POST", 
                    f"{GEMINI_BASE_URL}/chat/completions", 
                    json=gemini_body, 
                    headers=gemini_headers
                ) as r:
                    if r.status_code == 429:
                        print(f"[GeminiRouter] Stream rate limit (429) essai {attempt+1}. Attente {delay}s...")
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                    elif r.status_code >= 500:
                        print(f"[GeminiRouter] Stream serveur erreur ({r.status_code}) essai {attempt+1}. Attente {delay}s...")
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                        
                    r.raise_for_status()
                    success = True
                    async for chunk in r.aiter_bytes():
                        yield chunk
                    break
            except Exception as e:
                last_error = e
                print(f"[GeminiRouter] Echec stream Gemini (essai {attempt+1}) : {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2
                
        if not success:
            print(f"[GeminiRouter] Stream Gemini echoue.")
            error_msg = f"Gemini stream failed after {retries} retries. Error: {last_error}"
            yield json.dumps({"error": {"message": error_msg}}).encode('utf-8')
                
    return StreamingResponse(stream_generator(), media_type="text/event-stream")

@app.post("/v1/embeddings")
async def embeddings(request: Request):
    body = await request.json()
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

if __name__ == "__main__":
    print(f"Demarrage du Gemini Router sur le port 20130...")
    uvicorn.run(app, host="127.0.0.1", port=20130)
