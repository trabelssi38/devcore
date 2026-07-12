from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .schemas import ErrorBody, ErrorResponse, HealthResponse


API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"


def get_trace_id(request: Request) -> str:
    header_value = request.headers.get("X-Trace-Id", "").strip()
    return header_value or str(uuid4())


def build_error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict | None = None,
) -> JSONResponse:
    trace_id = get_trace_id(request)
    payload = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details or {}),
        trace_id=trace_id,
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def create_app() -> FastAPI:
    app = FastAPI(
        title="DEV_CORE API Gateway",
        version=API_VERSION,
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=f"{API_PREFIX}/redoc",
        openapi_url=f"{API_PREFIX}/openapi.json",
    )

    @app.get(f"{API_PREFIX}/health", response_model=HealthResponse, tags=["health"])
    async def health(request: Request) -> HealthResponse:
        return HealthResponse(trace_id=get_trace_id(request))

    @app.exception_handler(StarletteHTTPException)
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException | StarletteHTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else "http_error"
        return build_error_response(
            request=request,
            status_code=exc.status_code,
            code=code,
            message=str(exc.detail or "HTTP error"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return build_error_response(
            request=request,
            status_code=422,
            code="validation_error",
            message="Request validation failed",
            details={"errors": exc.errors()},
        )

    return app


app = create_app()
