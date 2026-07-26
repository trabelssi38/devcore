from uuid import uuid4
import json

import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .contracts import ContractCatalog, TaskListResponse, build_contract_catalog
from .github_webhooks import (
    GitHubWebhookAccepted,
    build_github_webhook_response,
    get_github_webhook_secret,
    verify_github_signature,
)
from .ports import FileTaskRepository, TaskBoardNotFound, TaskRepository, default_data_root
from .schemas import (
    ErrorBody,
    ErrorResponse,
    HealthResponse,
    WorkflowListResponse,
    WorkflowRunDetail,
)


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

    # Configure CORS middleware
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:20129",
        "http://127.0.0.1:20129",
    ]
    platform_root = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", str(Path(__file__).resolve().parents[3] / "DEV_CORE")))
    security_config_path = platform_root / "Config" / "security.json"
    if security_config_path.exists():
        try:
            sec_data = json.loads(security_config_path.read_text(encoding="utf-8"))
            sec_origins = sec_data.get("cors", {}).get("allowed_origins", [])
            allowed_origins.extend(sec_origins)
        except Exception:
            pass

    env_origins = os.environ.get("DEVCORE_CORS_ALLOWED_ORIGINS", "")
    if env_origins:
        allowed_origins.extend(o.strip() for o in env_origins.split(",") if o.strip())

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(dict.fromkeys(allowed_origins)),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-DevCore-Task", "X-DevCore-Budget-Alert", "X-Trace-Id"],
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

    @app.post(
        f"{API_PREFIX}/integrations/github/webhook",
        response_model=GitHubWebhookAccepted,
        status_code=202,
        tags=["integrations"],
    )
    async def github_webhook(request: Request) -> GitHubWebhookAccepted:
        body = await request.body()
        secret = get_github_webhook_secret()
        verify_github_signature(
            secret=secret,
            body=body,
            signature=request.headers.get("x-hub-signature-256"),
        )
        return build_github_webhook_response(
            event=request.headers.get("x-github-event"),
            delivery_id=request.headers.get("x-github-delivery"),
        )

    @app.get(f"{API_PREFIX}/workflows", response_model=WorkflowListResponse, tags=["workflows"])
    async def list_workflows() -> WorkflowListResponse:
        data_root = default_data_root()
        workflows_dir = data_root / "Workflows"
        workflows = []
        if workflows_dir.exists():
            for state_file in workflows_dir.glob("*.state.json"):
                try:
                    payload = json.loads(state_file.read_text(encoding="utf-8"))
                    workflows.append(WorkflowRunDetail(**payload))
                except Exception:
                    pass
        return WorkflowListResponse(workflows=workflows)

    @app.get(f"{API_PREFIX}/workflows/{{run_id}}", response_model=WorkflowRunDetail, tags=["workflows"])
    async def get_workflow(run_id: str, request: Request) -> WorkflowRunDetail:
        data_root = default_data_root()
        state_file = data_root / "Workflows" / f"{run_id}.state.json"
        if not state_file.exists():
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "workflow_not_found",
                    "message": f"Workflow run {run_id} not found",
                    "details": {"run_id": run_id},
                },
            )
        try:
            payload = json.loads(state_file.read_text(encoding="utf-8"))
            return WorkflowRunDetail(**payload)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "corrupted_workflow_state",
                    "message": f"Workflow state file is corrupted: {exc}",
                    "details": {"run_id": run_id},
                },
            )

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

    # Configure default metrics
    from .metrics import configure_metrics
    app = configure_metrics(app)

    return app


app = create_app()
