"""Two process-local Headroom profiles with a closed routing surface."""
import argparse
import asyncio
from collections import deque
import json
import os
from pathlib import Path
import re
import sys

# Direct script launch uses the same repository contract as the supervisor.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from devcore_engine.infra.llm_route_contract import PORTS, NATIVE_TARGETS, profile

try:
    from .router.policy import validate_auxiliary
    from .router.request_body import decode_json_async, STREAM_YIELD_EVERY
    from .router.admission import AdmissionGuard
except ImportError:  # Direct script entry point.
    from router.policy import validate_auxiliary
    from router.request_body import decode_json_async, STREAM_YIELD_EVERY
    from router.admission import AdmissionGuard

def native_provider(path: str) -> str | None:
    if path in ("/v1/responses", "/v1/chat/completions"):
        return "openai"
    if path == "/v1/messages":
        return "anthropic"
    if re.fullmatch(r"/v1beta/models/[^/]+:(generateContent|streamGenerateContent)", path):
        return "google-gemini"
    if path in ("/v1internal:generateContent", "/v1internal:streamGenerateContent"):
        return "google-cloudcode"
    return None


def validate_native_body(body: dict, model: str, provider: str):
    if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", model):
        raise ValueError("Explicit native model required")
    if model.startswith("devcore-") or "fallback_providers" in body:
        raise ValueError("Auxiliary routing is forbidden on the native path")
    if any(key in body for key in ("provider", "base_url", "api_base", "upstream", "upstream_model", "resolved_model", "mode", "capability_requirements")):
        raise ValueError("Native requests cannot override the routing policy")
    if provider == "anthropic" and not model.startswith("claude-"):
        raise ValueError("Messages requires a native Claude model")
    if provider == "openai" and not model.startswith(("gpt-", "codex-", "o1", "o3", "o4", "chatgpt-")):
        raise ValueError("OpenAI protocol requires a native OpenAI model")


class WebSocketPolicyRefusal(Exception):
    """Stop the downstream handler immediately after a rejected client frame."""


class RouteGuard:
    """ASGI guard; preserves streaming, rejects upstream overrides and admin writes."""

    def __init__(self, app, route: str, *, body_timeout: float = 30.0, max_requests: int = 8):
        profile(route)
        if not 0 < body_timeout <= 30:
            raise ValueError("Body timeout must be positive and at most 30 seconds")
        self.app, self.route = app, route
        self.body_timeout = body_timeout
        self.events = deque(maxlen=256)
        self.admission = AdmissionGuard(self._dispatch, max_requests=max_requests)

    async def __call__(self, scope, receive, send):
        return await self.admission(scope, receive, send)

    async def _dispatch(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        path = scope["path"]
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}

        async def refuse(message, status=400):
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            else:
                payload = json.dumps({"error": {"type": "routing_policy_error", "message": message}}).encode()
                await send({"type": "http.response.start", "status": status,
                            "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": payload})

        if any(k in headers for k in ("x-headroom-base-url", "x-headroom-original-path")):
            return await refuse("Per-request upstream overrides are forbidden")
        if scope["type"] == "http" and scope["method"] == "GET":
            if path in ("/health", "/healthz", "/devcore/routes"):
                ready = getattr(getattr(self.app, "state", None), "ready", False) is True
                payload = json.dumps({"service": "headroom-devcore", "route": self.route,
                    "status": "ready" if ready else "not_ready",
                    "port": PORTS[self.route], "profile": profile(self.route),
                    "recent_requests": list(self.events) if path == "/devcore/routes" else []}).encode()
                await send({"type": "http.response.start", "status": 200 if ready or path == "/devcore/routes" else 503,
                    "headers": [(b"content-type", b"application/json")]})
                return await send({"type": "http.response.body", "body": payload})
            if path == "/metrics":
                return await self.app(scope, receive, send)
            return await refuse("Endpoint outside the route contract", 404)
        provider = native_provider(path) if self.route == "native" else (
            "google-gemini" if path == "/v1/chat/completions" else None)
        if provider is None or (scope["type"] == "http" and scope["method"] != "POST"):
            return await refuse("Endpoint outside the route contract", 404)
        if scope["type"] == "websocket":
            if self.route != "native" or path != "/v1/responses":
                return await refuse("WebSocket is only available on the native Responses route")
            async def checked_receive():
                event = await receive()
                if event["type"] != "websocket.receive":
                    return event
                raw = event.get("text")
                try:
                    if not isinstance(raw, str) or len(raw.encode("utf-8")) > 16 * 1024 * 1024:
                        raise ValueError("Text WebSocket frame required, at most 16 MiB")
                    frame = await decode_json_async(raw)
                    if not isinstance(frame, dict) or frame.get("type") != "response.create":
                        raise ValueError("Only response.create frames are accepted")
                    payload = frame.get("response", frame)
                    if not isinstance(payload, dict):
                        raise ValueError("Response payload must be an object")
                    validate_native_body(frame, payload.get("model"), "openai")
                    validate_native_body(payload, payload.get("model"), "openai")
                except ValueError:
                    await send({"type": "websocket.close", "code": 1008})
                    raise WebSocketPolicyRefusal()
                return event
            try:
                return await self.app(scope, checked_receive, send)
            except WebSocketPolicyRefusal:
                return
        buffer = bytearray()
        events = 0
        try:
            # One deadline for the whole body, never reset by arriving chunks.
            async with asyncio.timeout(self.body_timeout):
                while True:
                    event = await receive()
                    if event["type"] == "http.disconnect":
                        return
                    chunk = event.get("body", b"")
                    if len(buffer) + len(chunk) > 16 * 1024 * 1024:
                        return await refuse("Request exceeds 16 MiB", 413)
                    buffer.extend(chunk)
                    events += 1
                    if events % STREAM_YIELD_EVERY == 0:
                        await asyncio.sleep(0)
                    if not event.get("more_body", False):
                        break
        except TimeoutError:
            return await refuse("Request body deadline exceeded", 408)
        raw = bytes(buffer)
        del buffer
        try:
            body = await decode_json_async(raw)
            if not isinstance(body, dict):
                raise ValueError("Expected JSON object")
            model = body.get("model")
            if provider == "google-gemini" and self.route == "native":
                model = path.split("/models/")[1].split(":")[0]
            if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", model):
                raise ValueError("Explicit model required")
            if self.route == "auxiliary":
                validate_auxiliary(body)
            else:
                validate_native_body(body, model, provider)
        except (ValueError, KeyError, IndexError) as exc:
            return await refuse(str(exc))
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": raw, "more_body": False}
            return await receive()

        async def observed_send(event):
            if event["type"] == "http.response.start":
                upstream = {k.decode().lower(): v.decode() for k, v in event.get("headers", [])}
                success = 200 <= event["status"] < 300
                resolved = model if success and self.route == "native" else upstream.get("x-devcore-resolved-model")
                self.events.append({"route": self.route, "requested_model": model,
                    "resolved_model": resolved, "provider": upstream.get("x-devcore-provider", provider),
                    "requested_provider": provider,
                    "upstream_provider": upstream.get("x-devcore-provider", provider) if success else None,
                    "task_type": body.get("task_type", model.removeprefix("devcore-") if self.route == "auxiliary" else "native"),
                    "status": event["status"]})
                if self.route == "native":
                    event = dict(event, headers=list(event.get("headers", [])) + [
                        (b"x-devcore-route", b"native"), (b"x-devcore-requested-model", model.encode()),
                        (b"x-devcore-provider", provider.encode()), (b"x-devcore-task-type", b"native")])
                    if resolved:
                        event["headers"].append((b"x-devcore-resolved-model", resolved.encode()))
            await send(event)

        await self.app(scope, replay, observed_send)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", choices=PORTS, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    config = profile(args.route)
    if args.check:
        print(json.dumps(config))
        return
    # Only this child process is changed. Ignore shared routing/settings overrides.
    for key in list(os.environ):
        if key.startswith("HEADROOM_") or key.endswith("_TARGET_API_URL"):
            os.environ.pop(key)
    import tempfile
    with tempfile.TemporaryDirectory(prefix=f"devcore-headroom-{args.route}-") as state:
        os.environ.update(HEADROOM_WORKSPACE_DIR=state, HEADROOM_CONFIG_DIR=state,
                          HEADROOM_STATELESS="true", HEADROOM_TELEMETRY="off",
                          HEADROOM_CC_SWITCH_RECONCILE="0", HEADROOM_LOSSLESS_ONLY="1")
        from headroom.proxy.models import ProxyConfig
        from headroom.proxy.server import create_app
        import uvicorn
        app = RouteGuard(create_app(ProxyConfig(**config)), args.route)
        from service_runtime import run_managed
        try:
            run_managed(app, host=config["host"], port=config["port"],
                service='headroom-' + args.route, proxy_headers=False)
        finally:
            # Headroom keeps a rotating proxy.log handler open on Windows.
            # Release it before TemporaryDirectory removes process-local state.
            import logging
            logger = logging.getLogger("headroom")
            for handler in list(logger.handlers):
                logger.removeHandler(handler)
                handler.close()


if __name__ == "__main__":
    main()
