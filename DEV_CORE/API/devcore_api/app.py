from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .contracts import ContractCatalog, TaskListResponse, build_contract_catalog
from .ports import FileTaskRepository, TaskBoardNotFound, TaskRepository
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


def create_app(task_repository: TaskRepository | None = None) -> FastAPI:
    task_repository = task_repository or FileTaskRepository()
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

    @app.get(f"{API_PREFIX}/contracts", response_model=ContractCatalog, tags=["contracts"])
    async def contracts() -> ContractCatalog:
        return build_contract_catalog()

    @app.get(f"{API_PREFIX}/tasks", response_model=TaskListResponse, tags=["tasks"])
    async def list_tasks(request: Request, project: str = "devcore") -> TaskListResponse:
        try:
            tasks = task_repository.list_tasks(project=project)
        except TaskBoardNotFound as exc:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "task_board_not_found",
                    "message": "Task board not found",
                    "details": {"project": project, "path": str(exc)},
                },
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "invalid_project",
                    "message": str(exc),
                    "details": {"project": project},
                },
            ) from exc
        return TaskListResponse(project=project, tasks=tasks)

    @app.exception_handler(StarletteHTTPException)
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException | StarletteHTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else "http_error"
        message = str(exc.detail or "HTTP error")
        details = None
        if isinstance(exc.detail, dict):
            code = str(exc.detail.get("code") or code)
            message = str(exc.detail.get("message") or message)
            details = dict(exc.detail.get("details") or {})
        return build_error_response(
            request=request,
            status_code=exc.status_code,
            code=code,
            message=message,
            details=details,
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
