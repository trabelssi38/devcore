#!/usr/bin/env python3
# anthropic_adapter.py -- DEV_CORE v10.0
# Traduit les requêtes Anthropic (port 8788) vers OpenAI (port 8787, Headroom)
# Puis traduit les réponses d'OpenAI vers Anthropic pour l'agent.

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx
import json
import asyncio
import os

app = FastAPI(title="DEV_CORE Anthropic to OpenAI Adapter")

HEADROOM_URL = os.environ.get("DEVCORE_HEADROOM_URL", "http://127.0.0.1:8787/v1")
client = httpx.AsyncClient(timeout=120.0)

def translate_request_to_openai(anthropic_body: dict) -> dict:
    openai_body = {}
    
    # 1. Messages mapping
    messages = []
    
    # Prepend system prompt if exists
    system_prompt = anthropic_body.get("system")
    if system_prompt:
        if isinstance(system_prompt, list):
            # Resolve if list of text blocks
            text_blocks = []
            for block in system_prompt:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_blocks.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_blocks.append(block)
            system_prompt = "\n".join(text_blocks)
        
        messages.append({"role": "system", "content": system_prompt})
        
    for msg in anthropic_body.get("messages", []):
        role = msg.get("role")
        content = msg.get("content")
        
        # Anthropic content can be string or list of content blocks
        if isinstance(content, list):
            text_blocks = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_blocks.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_blocks.append(block)
            content = "\n".join(text_blocks)
            
        messages.append({"role": role, "content": content})
        
    openai_body["messages"] = messages
    
    # 2. Model mapping
    openai_body["model"] = anthropic_body.get("model")
    
    # 3. Parameters mapping
    if "max_tokens" in anthropic_body:
        openai_body["max_tokens"] = anthropic_body["max_tokens"]
    if "temperature" in anthropic_body:
        openai_body["temperature"] = anthropic_body["temperature"]
    if "top_p" in anthropic_body:
        openai_body["top_p"] = anthropic_body["top_p"]
    if "stream" in anthropic_body:
        openai_body["stream"] = anthropic_body["stream"]
        
    return openai_body

def translate_response_to_anthropic(openai_resp: dict, model_name: str) -> dict:
    choices = openai_resp.get("choices", [])
    content_text = ""
    stop_reason = "end_turn"
    
    if choices:
        choice = choices[0]
        message = choice.get("message", {})
        content_text = message.get("content", "")
        finish_reason = choice.get("finish_reason")
        if finish_reason == "length":
            stop_reason = "max_tokens"
        elif finish_reason == "stop":
            stop_reason = "end_turn"
            
    usage = openai_resp.get("usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    
    anthropic_resp = {
        "id": openai_resp.get("id", "msg_default_id"),
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": content_text
            }
        ],
        "model": model_name,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }
    }
    return anthropic_resp

async def handle_streaming_translation(openai_stream, model_name: str, message_id: str):
    # Anthropic streaming events
    # 1. message_start
    # 2. content_block_start
    # 3. content_block_delta
    # 4. content_block_stop
    # 5. message_delta
    # 6. message_stop
    
    yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': message_id, 'type': 'message', 'role': 'assistant', 'content': [], 'model': model_name, 'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 0, 'output_tokens': 0}}})}\n\n".encode("utf-8")
    yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n".encode("utf-8")
    
    input_tokens = 0
    output_tokens = 0
    stop_reason = "end_turn"
    
    async for chunk in openai_stream.aiter_lines():
        if not chunk.strip():
            continue
        if chunk.startswith("data:"):
            data_str = chunk[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
                choices = data.get("choices", [])
                if choices:
                    choice = choices[0]
                    delta = choice.get("delta", {})
                    content_chunk = delta.get("content", "")
                    
                    if content_chunk:
                        yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': content_chunk}})}\n\n".encode("utf-8")
                        
                    finish_reason = choice.get("finish_reason")
                    if finish_reason:
                        if finish_reason == "length":
                            stop_reason = "max_tokens"
                        else:
                            stop_reason = "end_turn"
                            
                usage = data.get("usage")
                if usage:
                    input_tokens = usage.get("prompt_tokens", input_tokens)
                    output_tokens = usage.get("completion_tokens", output_tokens)
            except Exception:
                pass
                
    yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n".encode("utf-8")
    yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': stop_reason, 'stop_sequence': None}, 'usage': {'output_tokens': output_tokens}})}\n\n".encode("utf-8")
    yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n".encode("utf-8")

@app.post("/v1/messages")
async def messages_endpoint(request: Request):
    body = await request.json()
    headers = dict(request.headers)
    
    # 1. Translate request to OpenAI format
    openai_body = translate_request_to_openai(body)
    
    is_stream = body.get("stream", False)
    model_name = body.get("model", "claude-3-5-sonnet")
    
    # Forward headers (carrying task contexts if any)
    forward_headers = {
        "Content-Type": "application/json",
    }
    if "x-api-key" in headers:
        forward_headers["Authorization"] = f"Bearer {headers['x-api-key']}"
    # Carry task context header
    if "x-devcore-task" in headers:
        forward_headers["x-devcore-task"] = headers["x-devcore-task"]
        
    if is_stream:
        # Stream from Headroom (port 8787)
        async def stream_generator():
            try:
                async with client.stream(
                    "POST",
                    f"{HEADROOM_URL}/chat/completions",
                    json=openai_body,
                    headers=forward_headers
                ) as r:
                    r.raise_for_status()
                    message_id = f"msg_{os.urandom(8).hex()}"
                    async for chunk in handle_streaming_translation(r, model_name, message_id):
                        yield chunk
            except Exception as e:
                err_msg = f"Translation/Upstream streaming error: {e}"
                print(f"[AnthropicAdapter] Error: {err_msg}")
                yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': {'type': 'api_error', 'message': err_msg}})}\n\n".encode("utf-8")
                
        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    else:
        # Non-streaming call
        try:
            r = await client.post(
                f"{HEADROOM_URL}/chat/completions",
                json=openai_body,
                headers=forward_headers
            )
            r.raise_for_status()
            openai_resp = r.json()
            anthropic_resp = translate_response_to_anthropic(openai_resp, model_name)
            return Response(content=json.dumps(anthropic_resp), media_type="application/json")
        except Exception as e:
            err_msg = f"Translation/Upstream error: {e}"
            print(f"[AnthropicAdapter] Error: {err_msg}")
            return Response(
                content=json.dumps({"error": {"type": "api_error", "message": err_msg}}),
                status_code=502,
                media_type="application/json"
            )

if __name__ == "__main__":
    print("Demarrage du DEV_CORE Anthropic to OpenAI Adapter sur 127.0.0.1:8788...")
    uvicorn.run(app, host="127.0.0.1", port=8788)
