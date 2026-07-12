from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from typing import Any, Protocol
from uuid import uuid4

from fastapi import FastAPI, Request, Response


class SpanRecorder(Protocol):
    def record(self, name: str, attributes: dict[str, Any]) -> None: ...


class InMemorySpanRecorder:
    def __init__(self) -> None:
        self.spans: list[dict[str, Any]] = []

    def record(self, name: str, attributes: dict[str, Any]) -> None:
        self.spans.append({"name": name, "attributes": attributes})


@contextmanager
def recorded_span(recorder: SpanRecorder | None, name: str, attributes: dict[str, Any]):
    try:
        yield
    finally:
        if recorder is not None:
            recorder.record(name, attributes)


def configure_observability(app: FastAPI, *, recorder: SpanRecorder | None = None) -> FastAPI:
    @app.middleware("http")
    async def trace_middleware(request: Request, call_next: Callable) -> Response:
        trace_id = request.headers.get("X-Trace-Id", "").strip() or str(uuid4())
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        if recorder is not None:
            recorder.record(
                "http.request",
                {
                    "trace_id": trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                },
            )
        return response

    return app
