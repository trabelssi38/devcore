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
import time
import datetime
from pathlib import Path
from ai_capability_registry import load_capability_registry, select_backend_model

app = FastAPI(title="Gemini Router with Fallback")

DEV_CORE = os.environ.get("DEVCORE_PLATFORM_ROOT", "C:\\devcore\\DEV_CORE")
DEV_CORE_DATA = os.environ.get("DEVCORE_DATA_ROOT", "C:\\devcore\\DEV_CORE_DATA")
KEY_PATH = os.environ.get(
    "GEMINI_API_KEY_FILE",
    os.path.join(DEV_CORE, "Config", "gemini_api_key.txt"),
)

def load_api_key() -> str:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        return api_key.strip()
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

API_KEY = load_api_key()
PUBLIC_BIND_HOSTS = {"0.0.0.0", "::", ""}

def get_active_task_and_mode() -> tuple:
    active_project_path = "C:/devcore/DEV_CORE_DATA/Runtime/active_project.txt"
    project_name = "devcore"
    if os.path.exists(active_project_path):
        try:
            with open(active_project_path, "r", encoding="utf-8") as f:
                project_name = f.read().strip() or "devcore"
        except Exception:
            pass
            
    tasks_path = f"C:/devcore/DEV_CORE_DATA/Memory/{project_name}/tasks.json"
    if os.path.exists(tasks_path):
        try:
            with open(tasks_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                current_task_id = data.get("current_task")
                if current_task_id:
                    for t in data.get("tasks", []):
                        if t.get("id") == current_task_id:
                            return current_task_id, t.get("mode", "coding")
                return current_task_id or "Aucune", "coding"
        except Exception:
            pass
            
    return "Aucune", "coding"

def check_and_trigger_alerts(task_id: str, mode: str, total_tokens: int):
    thresholds = {
        "coding": 500000,
        "reasoning": 2000000,
        "bulk": 1000000
    }
    threshold = thresholds.get(mode, 1000000)
    if total_tokens > threshold:
        alert_msg = f"[DEV_CORE BUDGET ALERT] Task {task_id} ({mode} mode) has consumed {total_tokens} tokens, exceeding budget of {threshold}."
        print(alert_msg)
        
        alerts_dir = "C:/devcore/DEV_CORE_DATA/Logs/scripts"
        os.makedirs(alerts_dir, exist_ok=True)
        alerts_log = os.path.join(alerts_dir, "alerts.log")
        try:
            with open(alerts_log, "a", encoding="utf-8") as f:
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{ts}] {alert_msg}\n")
        except Exception as e:
            print(f"[GeminiRouter] Failed to write alert log: {e}")

def record_tokens(task_id: str, mode: str, prompt_tokens: int, completion_tokens: int):
    stats_path = "C:/devcore/DEV_CORE_DATA/Metrics/headroom_stats.json"
    os.makedirs(os.path.dirname(stats_path), exist_ok=True)
    
    for _ in range(5):
        try:
            stats = {"tasks": {}, "total_tokens": 0}
            if os.path.exists(stats_path):
                with open(stats_path, "r", encoding="utf-8-sig") as f:
                    content = f.read().strip()
                    if content:
                        stats = json.loads(content)
            
            if "tasks" not in stats:
                stats["tasks"] = {}
                
            if task_id not in stats["tasks"]:
                stats["tasks"][task_id] = {
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "total_tokens": 0,
                    "calls": 0,
                    "mode": mode
                }
                
            task_stats = stats["tasks"][task_id]
            task_stats["tokens_in"] += prompt_tokens
            task_stats["tokens_out"] += completion_tokens
            task_stats["total_tokens"] += (prompt_tokens + completion_tokens)
            task_stats["calls"] += 1
            task_stats["mode"] = mode
            
            stats["total_tokens"] = sum(t["total_tokens"] for t in stats["tasks"].values())
            
            with open(stats_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
                
            check_and_trigger_alerts(task_id, mode, task_stats["total_tokens"])
            break
        except Exception as e:
            time.sleep(0.1)

def has_budget_alert(task_id: str) -> bool:
    stats_path = "C:/devcore/DEV_CORE_DATA/Metrics/headroom_stats.json"
    if not os.path.exists(stats_path):
        return False
    try:
        with open(stats_path, "r", encoding="utf-8-sig") as f:
            stats = json.load(f)
            task_stats = stats.get("tasks", {}).get(task_id)
            if task_stats:
                mode = task_stats.get("mode", "coding")
                total = task_stats.get("total_tokens", 0)
                thresholds = {
                    "coding": 500000,
                    "reasoning": 2000000,
                    "bulk": 1000000
                }
                threshold = thresholds.get(mode, 1000000)
                return total > threshold
    except Exception:
        pass
    return False


def read_network_config() -> dict:
    config_path = Path(DEV_CORE) / "Config" / "network.json"
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[GeminiRouter] Unable to read network config {config_path}: {exc}")
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

GEMINI_BASE_URL = os.environ.get(
    "GEMINI_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai/v1",
)

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
    "devcore-always-on": "gemini-2.5-pro",
    "devcore-reasoning": "gemini-2.5-pro",
    "devcore-coding": "gemini-2.5-pro",
    "devcore-bulk": "gemini-2.5-flash",
}

MODE_MODEL_MAP = {
    "reasoning": "devcore-reasoning",
    "coding": "devcore-coding",
    "bulk": "devcore-bulk",
    "plan": "devcore-reasoning",
}

def map_for_gemini(body: dict, is_chat: bool) -> dict:
    mapped = body.copy()
    if is_chat:
        requested_mode = str(body.get("mode") or "").strip().lower()
        original_model = body.get("model") or MODE_MODEL_MAP.get(requested_mode) or "devcore-always-on"
        selection_body = body.copy()
        if body.get("model"):
            selection_body["model"] = original_model
        backend_model, selected = select_backend_model(selection_body, load_capability_registry())
        mapped["model"] = backend_model or MODEL_MAP.get(original_model, "gemini-2.5-flash")
        mapped.pop("mode", None)
        # Supprimer max_tokens si trop petit pour éviter les erreurs Gemini
        if "max_tokens" in mapped and mapped["max_tokens"] < 50:
            del mapped["max_tokens"]
        for internal_key in (
            "workflow_step",
            "capability_requirements",
            "requirements",
            "workflow_requirements",
            "language",
            "specialty",
            "optimize_for",
            "min_context_tokens",
        ):
            mapped.pop(internal_key, None)
    else:
        mapped["model"] = "gemini-embedding-001"
    return mapped

async def call_with_fallback(path: str, body: dict, headers: dict, is_chat: bool) -> Response:
    if not API_KEY:
        return Response(
            content=json.dumps({
                "error": {
                    "message": "GEMINI_API_KEY or GEMINI_API_KEY_FILE is required",
                    "type": "configuration_error"
                }
            }),
            status_code=503,
            media_type="application/json"
        )

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
            resp_content = r.content
            
            # Extract and record tokens
            task_id, mode = get_active_task_and_mode()
            try:
                resp_json = json.loads(resp_content.decode("utf-8"))
                usage = resp_json.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                
                if prompt_tokens == 0 and is_chat:
                    prompt_text = json.dumps(gemini_body.get("messages", []))
                    prompt_tokens = max(1, len(prompt_text) // 4)
                if completion_tokens == 0 and is_chat:
                    choices = resp_json.get("choices", [])
                    if choices:
                        content_text = choices[0].get("message", {}).get("content", "")
                        completion_tokens = max(1, len(content_text) // 4)
                
                if prompt_tokens > 0 or completion_tokens > 0:
                    record_tokens(task_id, mode, prompt_tokens, completion_tokens)
            except Exception as e:
                print(f"[GeminiRouter] Error recording tokens: {e}")
                
            headers_out = {
                "Content-Type": "application/json",
                "X-DevCore-Task": task_id
            }
            if has_budget_alert(task_id):
                headers_out["X-DevCore-Budget-Alert"] = "True"
                
            return Response(content=resp_content, status_code=r.status_code, headers=headers_out)
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
    
    async def stream_generator():
        success = False
        retries = 3
        delay = 1.0
        last_error = None
        
        prompt_tokens = 0
        try:
            prompt_text = json.dumps(gemini_body.get("messages", []))
            prompt_tokens = max(1, len(prompt_text) // 4)
        except Exception:
            pass
            
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
                    
                    accumulated_text = ""
                    usage = None
                    
                    async for chunk in r.aiter_bytes():
                        yield chunk
                        try:
                            lines = chunk.decode("utf-8", errors="ignore").split("\n")
                            for line in lines:
                                if line.startswith("data:"):
                                    data_str = line[5:].strip()
                                    if data_str == "[DONE]":
                                        continue
                                    data_json = json.loads(data_str)
                                    if "usage" in data_json and data_json["usage"]:
                                        usage = data_json["usage"]
                                    choices = data_json.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        if "content" in delta:
                                            accumulated_text += delta["content"]
                        except Exception:
                            pass
                            
                    try:
                        completion_tokens = 0
                        if usage:
                            prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                            completion_tokens = usage.get("completion_tokens", 0)
                        else:
                            completion_tokens = max(1, len(accumulated_text) // 4)
                        
                        task_id, mode = get_active_task_and_mode()
                        record_tokens(task_id, mode, prompt_tokens, completion_tokens)
                    except Exception as e:
                        print(f"[GeminiRouter] Error logging streaming tokens: {e}")
                        
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
    uvicorn.run(app, host=get_bind_host(), port=20130)
