import os
import sys
import json
import time
import asyncio
import datetime
from dataclasses import dataclass
from pathlib import Path
import httpx
from fastapi import Response

from ai_capability_registry import load_capability_registry, select_backend_model
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
    ACTIVE_PROJECT_PATH,
    TASKS_DIR,
    ALERTS_LOG,
    STATS_PATH,
    EPHEMERAL_PATH,
    PROTOCOL_LOG
)

# Async HTTP Client with timeouts for long contexts
client = httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0))

class SlidingWindowRateLimiter:
    """Proactive RPM and TPM rate limiter using sliding window."""
    def __init__(self, max_rpm: int = 8, max_tpm: int = 200_000):
        self.max_rpm = max_rpm
        self.max_tpm = max_tpm
        self._timestamps: list[float] = []
        self._tokens: list[tuple[float, int]] = []
        self._lock = asyncio.Lock()

    async def wait_if_needed(self, estimated_tokens: int = 500):
        async with self._lock:
            now = time.time()
            cutoff = now - 60.0
            self._timestamps = [t for t in self._timestamps if t > cutoff]
            self._tokens = [(t, n) for t, n in self._tokens if t > cutoff]

            if len(self._timestamps) >= self.max_rpm:
                wait_time = self._timestamps[0] - cutoff
                if wait_time > 0:
                    print(f"[RateLimiter] Max RPM ({self.max_rpm}) reached. Waiting {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time + 0.1)

            current_tpm = sum(n for _, n in self._tokens)
            if current_tpm + estimated_tokens > self.max_tpm:
                wait_time = self._tokens[0][0] - cutoff if self._tokens else 5.0
                if wait_time > 0:
                    print(f"[RateLimiter] Max TPM ({self.max_tpm}) reached. Waiting {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time + 0.1)

            self._timestamps.append(time.time())

    async def record_tokens(self, token_count: int):
        async with self._lock:
            self._tokens.append((time.time(), token_count))

rate_limiter = SlidingWindowRateLimiter()

def get_active_task_and_mode() -> tuple:
    project_name = "devcore"
    if ACTIVE_PROJECT_PATH.exists():
        try:
            project_name = ACTIVE_PROJECT_PATH.read_text(encoding="utf-8-sig").strip() or "devcore"
        except Exception:
            pass
            
    tasks_path = TASKS_DIR / project_name / "tasks.json"
    if tasks_path.exists():
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
    threshold = BUDGET_THRESHOLDS.get(mode, 1000000)
    if total_tokens > threshold:
        alert_msg = f"[DEV_CORE BUDGET ALERT] Task {task_id} ({mode} mode) has consumed {total_tokens} tokens, exceeding budget of {threshold}."
        print(alert_msg)
        
        try:
            ALERTS_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(ALERTS_LOG, "a", encoding="utf-8") as f:
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{ts}] {alert_msg}\n")
        except Exception as e:
            print(f"[GeminiRouter] Failed to write alert log: {e}", file=sys.stderr)

def record_tokens(task_id: str, mode: str, prompt_tokens: int, completion_tokens: int):
    try:
        STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    
    for _ in range(5):
        try:
            stats = {"tasks": {}, "total_tokens": 0}
            if STATS_PATH.exists():
                with open(STATS_PATH, "r", encoding="utf-8-sig") as f:
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
            
            with open(STATS_PATH, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
                
            check_and_trigger_alerts(task_id, mode, task_stats["total_tokens"])
            break
        except Exception:
            time.sleep(0.1)

def has_budget_alert(task_id: str) -> bool:
    if not STATS_PATH.exists():
        return False
    try:
        with open(STATS_PATH, "r", encoding="utf-8-sig") as f:
            stats = json.load(f)
            task_stats = stats.get("tasks", {}).get(task_id)
            if task_stats:
                mode = task_stats.get("mode", "coding")
                total = task_stats.get("total_tokens", 0)
                threshold = BUDGET_THRESHOLDS.get(mode, 1000000)
                return total > threshold
    except Exception:
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
    current_task, mode = get_active_task_and_mode()
    if current_task and current_task != "Aucune":
        return ProtocolStatus(
            compliant=True,
            task_id=current_task,
            mode=mode,
            ephemeral=False,
            violation_count=0
        )
    
    try:
        EPHEMERAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    
    session_data = {}
    if EPHEMERAL_PATH.exists():
        try:
            session_data = json.loads(EPHEMERAL_PATH.read_text(encoding="utf-8"))
        except Exception:
            session_data = {}
            
    if not session_data:
        session_id = f"EPH-{int(time.time())}"
        session_data = {
            "session_id": session_id,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "violation_count": 1,
            "mode": mode
        }
    else:
        session_data["violation_count"] = session_data.get("violation_count", 0) + 1
        
    try:
        EPHEMERAL_PATH.write_text(json.dumps(session_data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[GeminiRouter] Failed to write ephemeral session: {e}", file=sys.stderr)
        
    return ProtocolStatus(
        compliant=False,
        task_id=session_data.get("session_id", "EPH-000"),
        mode=mode,
        ephemeral=True,
        violation_count=session_data.get("violation_count", 1)
    )

def inject_protocol_reminder(body: dict, status: ProtocolStatus) -> dict:
    if status.compliant:
        return body
        
    if status.violation_count % 5 == 1:
        reminder_text = (
            f"[DEV_CORE PROTOCOLE] Aucune tâche formelle n'est active.\n"
            f"Votre travail est actuellement suivi sous la session éphémère {status.task_id}.\n"
            f"Pour activer le tracking complet et respecter le protocole DEV_CORE, exécutez :\n"
            f"  python DEV_CORE/Scripts/tasks.py start \"<description de la tâche>\""
        )
        body_copy = body.copy()
        messages = list(body_copy.get("messages", []))
        messages.insert(0, {"role": "system", "content": reminder_text})
        body_copy["messages"] = messages
        return body_copy
    return body

def log_protocol_violation(status: ProtocolStatus):
    try:
        PROTOCOL_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{ts}] VIOLATION task_id={status.task_id} count={status.violation_count} ephemeral={status.ephemeral}\n"
        with open(PROTOCOL_LOG, "a", encoding="utf-8") as f:
            f.write(msg)
    except Exception as e:
        print(f"[GeminiRouter] Failed to log protocol violation: {e}", file=sys.stderr)

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

async def _try_provider_request(url: str, body: dict, api_key: str, provider_name: str) -> Response | None:
    """Execute request to an OpenAI-compatible provider with standard response building."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    r = await client.post(url, json=body, headers=headers)
    if r.status_code == 200:
        task_id, mode = get_active_task_and_mode()
        try:
            resp_json = r.json()
            usage = resp_json.get("usage", {})
            p_tok = usage.get("prompt_tokens", 0)
            c_tok = usage.get("completion_tokens", 0)
            if p_tok > 0 or c_tok > 0:
                record_tokens(task_id, mode, p_tok, c_tok)
        except Exception:
            pass
        out_headers = {"Content-Type": "application/json", "X-DevCore-Task": task_id, "X-DevCore-Provider": provider_name}
        if has_budget_alert(task_id):
            out_headers["X-DevCore-Budget-Alert"] = "True"
        return Response(content=r.content, status_code=200, headers=out_headers)
    else:
        print(f"[GeminiRouter] Provider {provider_name} returned status {r.status_code}: {r.text[:200]}")
        return None

async def call_with_fallback(path: str, body: dict, headers: dict, is_chat: bool) -> Response:
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
                r = await client.post(url, json=gemini_body, headers=gemini_headers)

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
                task_id, mode = get_active_task_and_mode()
                try:
                    resp_json = json.loads(resp_content.decode("utf-8"))
                    usage = resp_json.get("usage", {})
                    p_tokens = usage.get("prompt_tokens", 0)
                    c_tokens = usage.get("completion_tokens", 0)
                    if p_tokens == 0 and is_chat:
                        p_tokens = est_tokens
                    if c_tokens == 0 and is_chat:
                        choices = resp_json.get("choices", [])
                        if choices:
                            c_tokens = max(1, len(choices[0].get("message", {}).get("content", "")) // 4)
                    tot_tokens = p_tokens + c_tokens
                    if tot_tokens > 0:
                        record_tokens(task_id, mode, p_tokens, c_tokens)
                        await rate_limiter.record_tokens(tot_tokens)
                except Exception as e:
                    print(f"[GeminiRouter] Error recording tokens: {e}")

                headers_out = {
                    "Content-Type": "application/json",
                    "X-DevCore-Task": task_id,
                    "X-DevCore-Provider": "google-gemini"
                }
                if has_budget_alert(task_id):
                    headers_out["X-DevCore-Budget-Alert"] = "True"

                return Response(content=resp_content, status_code=r.status_code, headers=headers_out)
            except Exception as e:
                print(f"[GeminiRouter] Gemini call attempt {attempt+1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2

    # 2. Fallback: Cerebras
    if CEREBRAS_API_KEY and is_chat:
        print("[GeminiRouter] Bascule automatique vers le provider de secours #1 : Cerebras (llama-3.3-70b)...")
        try:
            cerebras_body = body.copy()
            cerebras_body["model"] = "llama-3.3-70b"
            for k in ("mode", "workflow_step", "capability_requirements", "requirements"):
                cerebras_body.pop(k, None)
            res = await _try_provider_request("https://api.cerebras.ai/v1/chat/completions", cerebras_body, CEREBRAS_API_KEY, "cerebras")
            if res:
                return res
        except Exception as e:
            print(f"[GeminiRouter] Cerebras fallback failed: {e}")

    # 3. Fallback: NVIDIA NIM
    if NVIDIA_API_KEY and is_chat:
        print("[GeminiRouter] Bascule automatique vers le provider de secours #2 : NVIDIA NIM (meta/llama-3.3-70b-instruct)...")
        try:
            nvidia_body = body.copy()
            nvidia_body["model"] = "meta/llama-3.3-70b-instruct"
            for k in ("mode", "workflow_step", "capability_requirements", "requirements"):
                nvidia_body.pop(k, None)
            res = await _try_provider_request("https://integrate.api.nvidia.com/v1/chat/completions", nvidia_body, NVIDIA_API_KEY, "nvidia-nim")
            if res:
                return res
        except Exception as e:
            print(f"[GeminiRouter] NVIDIA NIM fallback failed: {e}")

    error_msg = "All completion providers (Gemini, Cerebras, NVIDIA NIM) failed or returned errors."
    print(f"[GeminiRouter] {error_msg}")
    return Response(
        content=json.dumps({"error": {"message": error_msg, "type": "multi_provider_error"}}),
        status_code=502,
        media_type="application/json"
    )
