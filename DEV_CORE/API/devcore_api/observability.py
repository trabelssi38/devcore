from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from typing import Any, Protocol

from fastapi import FastAPI, Request, Response

from .correlation import CorrelationContext


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
        context = CorrelationContext.from_headers(request.headers)
        response = await call_next(request)
        response.headers["X-Trace-Id"] = context.trace_id
        if recorder is not None:
            attributes = context.as_span_attributes()
            attributes.update(
                {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                }
            )
            recorder.record(
                "http.request",
                attributes,
            )
        return response

    return app
