import json
import asyncio
import httpx
from contextlib import aclosing
from typing import AsyncGenerator
from .config import GEMINI_BASE_URL
from .policy import TASK_TYPES
from .sse_usage import SseUsage
from .upstream_body import UpstreamBodyRefusal, validate_response_headers
from .rate_limit import RateLimitRefusal
from .providers import (
    client,
    get_active_task_and_mode,
    record_tokens
)

async def stream_generator(gemini_body: dict, gemini_headers: dict, *, limiter=None,
                           estimated_tokens=500, deadline_seconds=120.0,
                           max_response_bytes=16 * 1024 * 1024, accounting_mode="auxiliary") -> AsyncGenerator[bytes, None]:
    if type(deadline_seconds) not in (int, float) or not 0 < deadline_seconds <= 120:
        raise ValueError('Stream deadline must be positive and at most 120 seconds')
    if type(max_response_bytes) is not int or not 1 <= max_response_bytes <= 16 * 1024 * 1024:
        raise ValueError('Invalid stream response byte capacity')
    if accounting_mode not in (*TASK_TYPES.values(), 'auxiliary'):
        raise ValueError('Invalid auxiliary accounting mode')
    loop = asyncio.get_running_loop()
    deadline = loop.time() + deadline_seconds
    received_bytes = 0
    async with aclosing(_stream_generator(gemini_body, gemini_headers,
        limiter=limiter, estimated_tokens=estimated_tokens, max_response_bytes=max_response_bytes, accounting_mode=accounting_mode)) as source:
        while True:
            remaining = deadline - loop.time()
            try:
                if remaining <= 0:
                    raise TimeoutError
                chunk = await asyncio.wait_for(anext(source), remaining)
            except StopAsyncIteration:
                return
            except UpstreamBodyRefusal:
                await source.aclose()
                error = {'error': {'type': 'provider_response_refused',
                    'message': 'Provider stream transport refused'}}
                yield b'data: ' + json.dumps(error).encode('utf-8') + b'\n\n'
                return
            except TimeoutError:
                # Close upstream before reporting expiration. No timeout context
                # spans yield: it must never cancel the caller while it sends.
                await source.aclose()
                error = {'error': {'type': 'provider_deadline',
                    'message': 'Provider stream deadline exceeded'}}
                yield b'data: ' + json.dumps(error).encode('utf-8') + b'\n\n'
                return
            if received_bytes + len(chunk) > max_response_bytes:
                await source.aclose()
                error = {'error': {'type': 'provider_response_too_large',
                    'message': 'Provider stream response exceeds byte capacity'}}
                yield b'data: ' + json.dumps(error).encode('utf-8') + b'\n\n'
                return
            received_bytes += len(chunk)
            yield chunk


async def _stream_generator(gemini_body: dict, gemini_headers: dict, *, limiter=None, estimated_tokens=500,
                            max_response_bytes=16 * 1024 * 1024, accounting_mode="auxiliary") -> AsyncGenerator[bytes, None]:
    success = False
    retries = 3
    delay = 1.0
    
    delivered = False
        
    for attempt in range(retries):
        try:
            if attempt and limiter is not None:
                await limiter.wait_if_needed(estimated_tokens)
            async with client.stream(
                "POST", 
                f"{GEMINI_BASE_URL}/chat/completions", 
                json=gemini_body, 
                headers={**gemini_headers, 'Accept-Encoding': 'identity'},
                follow_redirects=False
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
                
                declared = validate_response_headers(r.headers, max_response_bytes)
                received = 0
                observed = SseUsage()
                
                async for chunk in r.aiter_raw():
                    if declared is not None and received + len(chunk) > declared:
                        raise UpstreamBodyRefusal('Provider stream length mismatch')
                    received += len(chunk)
                    delivered = True
                    yield chunk
                    await observed.feed_async(chunk)
                        
                if declared is not None and received != declared:
                    raise UpstreamBodyRefusal('Provider stream length mismatch')
                try:
                    usage = observed.result()
                    if usage is not None:
                        task_id, mode = 'unattributed.' + accounting_mode, accounting_mode
                        record_tokens(task_id, mode, *usage)
                        if limiter is not None:
                            await limiter.record_tokens(sum(usage))
                except Exception:
                    print("[GeminiRouter] Streaming token recording failed")
                    
                success = True
                break
        except httpx.RemoteProtocolError as exc:
            raise UpstreamBodyRefusal('Invalid provider stream framing') from exc
        except UpstreamBodyRefusal:
            raise
        except RateLimitRefusal as exc:
            error = {'error': {'type': 'local_rate_limit',
                'message': 'Local provider admission saturated', 'retry_after': exc.retry_after}}
            yield b'data: ' + json.dumps(error).encode('utf-8') + b'\n\n'
            return
        except Exception:
            if delivered:
                # Retrying after forwarding bytes duplicates part of the response.
                raise
            print(f"[GeminiRouter] Gemini stream attempt {attempt+1} failed")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
            
    if not success:
        print(f"[GeminiRouter] Stream Gemini echoue.")
        error_msg = f"Gemini stream failed after {retries} retries."
        yield json.dumps({"error": {"message": error_msg}}).encode('utf-8')
