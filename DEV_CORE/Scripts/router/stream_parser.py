import json
import asyncio
from typing import AsyncGenerator
from .config import GEMINI_BASE_URL
from .providers import (
    client,
    rate_limiter,
    get_active_task_and_mode,
    record_tokens
)

async def stream_generator(gemini_body: dict, gemini_headers: dict) -> AsyncGenerator[bytes, None]:
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
                            if not line.startswith("data:"):
                                continue
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
