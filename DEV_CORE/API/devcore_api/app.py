from uuid import uuid4
import json

import os
import asyncio
import re
import sys
import time
import sqlite3
from contextlib import asynccontextmanager, closing
from pathlib import Path
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse
from urllib.parse import urlencode
from starlette.exceptions import HTTPException as StarletteHTTPException

DEVCORE_BASE = Path(__file__).resolve().parents[2]
if str(DEVCORE_BASE) not in sys.path:
    sys.path.insert(0, str(DEVCORE_BASE))

from devcore_engine.services.task_mutations import (
    TaskMutationConflict,
    complete_task_usecase,
    delete_task_usecase,
    transition_task_usecase,
    validate_safe_id as validate_safe_mutation_id,
)
from devcore_engine.services.postgres_task_mutations import PostgresTaskMutations
from devcore_engine.services.postgres_project_reads import PostgresProjectReader
from devcore_engine.services.postgres_project_events import PostgresProjectEventReader, validate_event_cursor
from devcore_engine.services.postgres_dashboard import PostgresDashboardProjection

from .contracts import ContractCatalog, TaskListResponse, build_contract_catalog
from .team_cockpit import render_team_cockpit
from .team_login import COCKPIT_PATHS, render_team_login
from .team_gemini import GeminiRouteUnavailable, generate_project_summary
from .github_webhooks import (
    GitHubWebhookAccepted,
    build_github_webhook_response,
    get_github_webhook_secret,
    verify_github_signature,
)
from .ports import (
    TaskBoardInvalid,
    TaskBoardNotFound,
    TaskRepository,
    PostgresTaskRepository,
    canonical_db_status,
    configured_task_repository,
    default_data_root,
    normalize_status_filter,
    validate_project_id,
)
from .schemas import (
    ErrorBody,
    ErrorResponse,
    HealthResponse,
    RouteCatalogResponse,
    RouteInfo,
    RunDetailResponse,
    RunListResponse,
    RunSubmissionRequest,
    WorkflowListResponse,
    WorkflowRunDetail,
)


API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"
SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def resolve_api_db_path(task_repository: TaskRepository | None = None) -> Path | None:
    if (
        os.environ.get("DEVCORE_TASK_READ_MODE", "").strip().lower() == "postgres"
        or isinstance(task_repository, PostgresTaskRepository)
    ):
        raise RuntimeError("PostgreSQL team task routes cannot use the SQLite task database")
    if hasattr(task_repository, "db_path"):
        return Path(task_repository.db_path)
    if hasattr(task_repository, "sql_repository") and hasattr(task_repository.sql_repository, "db_path"):
        return Path(task_repository.sql_repository.db_path)
    env_db = os.environ.get("DEVCORE_SQLITE_DB_PATH")
    if env_db and Path(env_db).is_file():
        return Path(env_db)
    from devcore_engine.db import get_local_data_root
    local_db = get_local_data_root() / "devcore.db"
    if local_db.is_file():
        return local_db
    return None


def load_project_workflow(state_file: Path, project: str) -> WorkflowRunDetail | None:
    """Legacy states without a verified project remain unavailable to project APIs."""
    try:
        payload = json.loads(state_file.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return None
        if payload.get("project") != project:
            return None
        if state_file.name != f"{payload.get('run_id')}.state.json":
            return None
        return WorkflowRunDetail(**payload)
    except (OSError, ValueError, TypeError):
        return None


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
    headers: dict | None = None,
) -> JSONResponse:
    trace_id = get_trace_id(request)
    payload = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details or {}),
        trace_id=trace_id,
    )
    content = payload.model_dump()
    content["detail"] = {"code": code, "message": message, "details": details or {}}
    content["code"] = code
    content["message"] = message
    return JSONResponse(status_code=status_code, content=content, headers=headers)


def is_auth_enforced() -> bool:
    """Check if server-side project authorization must be enforced (Lot L4)."""
    return (
        os.environ.get("DEVCORE_REQUIRE_AUTH", "").lower() in {"1", "true", "yes"}
        or os.environ.get("DEVCORE_AUTH_MODE", "").lower() == "individual"
        or os.environ.get("DEVCORE_DASHBOARD_AUTH_PROFILE", "").lower() == "individual"
        or os.environ.get("DEVCORE_REQUIRE_AUTH_ALL", "").lower() == "1"
    )


def resolve_identity_store_path() -> Path | None:
    env_store = os.environ.get("DEVCORE_IDENTITY_STORE")
    if env_store and Path(env_store).is_file():
        return Path(env_store)
    from devcore_engine.db import get_local_data_root
    local_root = get_local_data_root()
    for name in ("identity.db", "individual_identity.db"):
        candidate = local_root / "Security" / name
        if candidate.is_file():
            return candidate
        candidate2 = local_root / name
        if candidate2.is_file():
            return candidate2
    if env_store:
        return Path(env_store)
    return None


def resolve_postgres_identity_dsn() -> str | None:
    if os.environ.get("DEVCORE_IDENTITY_READ_MODE", "").lower() != "postgres":
        return None
    value = os.environ.get("DEVCORE_DATABASE_URL", "").strip()
    return value or None


def trusted_session_origin(
    request: Request,
    allowed_origins: list[str] | None = None,
    *,
    require_origin: bool = False,
) -> str:
    origin = f"{request.url.scheme}://{request.url.netloc}"
    supplied = request.headers.get("Origin")
    if require_origin and not supplied:
        raise HTTPException(status_code=403, detail="Invalid session origin")
    if supplied:
        allowed = set(allowed_origins or []) | {
            origin,
            "http://127.0.0.1:20129",
            "http://localhost:20129",
            "http://127.0.0.1:20131",
            "http://localhost:20131",
            "http://testserver",
            "testserver",
        }
        if supplied != origin and supplied not in allowed:
            raise HTTPException(status_code=403, detail="Invalid session origin")
        origin = supplied
    if request.url.scheme != "https" and request.url.hostname not in {"localhost", "127.0.0.1", "::1", "testserver"}:
        raise HTTPException(status_code=403, detail="Session requires HTTPS or loopback")
    return origin


def create_app(
    task_repository: TaskRepository | None = None,
    require_auth: bool | None = None,
    run_engine: object | None = None,
    start_run_worker: bool = True,
) -> FastAPI:
    from devcore_engine.runs import (
        DurableRunEngine,
        RunBackpressureError,
        RunNotFoundError,
        RunRecord,
        RunSubmission,
        RunTransitionError,
    )

    active_run_engine: DurableRunEngine | None = run_engine  # type: ignore

    def get_run_engine() -> DurableRunEngine:
        nonlocal active_run_engine
        if active_run_engine is None:
            active_run_engine = DurableRunEngine()
        return active_run_engine

    def team_task_mutations() -> PostgresTaskMutations | None:
        if not (
            isinstance(task_repository, PostgresTaskRepository)
            or os.environ.get("DEVCORE_TASK_READ_MODE", "").strip().lower() == "postgres"
        ):
            return None
        dsn = os.environ.get("DEVCORE_DATABASE_URL", "").strip()
        if not dsn:
            raise ValueError("DEVCORE_DATABASE_URL is required for PostgreSQL task mutations")
        return PostgresTaskMutations(dsn)

    def team_project_reader() -> PostgresProjectReader | None:
        if not (
            isinstance(task_repository, PostgresTaskRepository)
            or os.environ.get("DEVCORE_TASK_READ_MODE", "").strip().lower() == "postgres"
        ):
            return None
        dsn = os.environ.get("DEVCORE_DATABASE_URL", "").strip()
        if not dsn:
            raise ValueError("DEVCORE_DATABASE_URL is required for PostgreSQL project reads")
        return PostgresProjectReader(dsn)

    project_stream_slots = asyncio.Semaphore(32)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if start_run_worker:
            get_run_engine().start_worker()
        try:
            yield
        finally:
            if active_run_engine is not None:
                active_run_engine.stop_worker()

    task_repository = task_repository if task_repository is not None else configured_task_repository()
    app = FastAPI(
        title="DEV_CORE API Gateway",
        version=API_VERSION,
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=f"{API_PREFIX}/redoc",
        openapi_url=f"{API_PREFIX}/openapi.json",
        lifespan=lifespan,
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

    @app.middleware("http")
    async def project_authorization_gate(request: Request, call_next):
        enforced = require_auth if require_auth is not None else is_auth_enforced()
        if not enforced:
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        method = request.method

        public_exact = {
            "/login",
            f"{API_PREFIX}/health",
            "/api/health",
            f"{API_PREFIX}/contracts",
            "/api/contracts",
            f"{API_PREFIX}/routes",
            "/api/routes",
            f"{API_PREFIX}/integrations/github/webhook",
        }
        if (
            path in public_exact
            or path.startswith(f"{API_PREFIX}/docs")
            or path.startswith(f"{API_PREFIX}/redoc")
            or path == f"{API_PREFIX}/openapi.json"
        ):
            return await call_next(request)

        if path in {"/api/auth/session", f"{API_PREFIX}/auth/session"}:
            return await call_next(request)

        query_project = request.query_params.get("project")
        body_project = None
        body_data: dict = {}
        if method in {"POST", "PUT", "DELETE", "PATCH"}:
            try:
                body = await request.body()
                if len(body) > 1024 * 1024:
                    return build_error_response(
                        request=request, status_code=413, code="request_too_large", message="Request body too large"
                    )
                if body:
                    data = json.loads(body)
                    if isinstance(data, dict):
                        body_data = data
                        body_project = data.get("project") or data.get("project_id")
            except Exception:
                pass

        if query_project and body_project and query_project != body_project:
            return build_error_response(
                request=request,
                status_code=400,
                code="project_mismatch",
                message=f"Query project '{query_project}' does not match body project '{body_project}'",
            )

        project = query_project or body_project

        if not project:
            return build_error_response(
                request=request, status_code=400, code="invalid_arguments", message="Explicit project required"
            )

        try:
            project = validate_project_id(project)
        except ValueError as exc:
            return build_error_response(
                request=request, status_code=400, code="invalid_project", message=str(exc)
            )

        request.state.authorized_project = project

        if method in {"POST", "DELETE"} and not path.startswith(f"{API_PREFIX}/runs") and path not in {f"{API_PREFIX}/tasks", f"{API_PREFIX}/tasks/next"}:
            if body_data:
                version = body_data.get("expected_version")
                if version is not None and (type(version) is not int or version < 1):
                    return build_error_response(
                        request=request,
                        status_code=400,
                        code="invalid_arguments",
                        message="Positive expected_version required",
                    )

        if path in {f"{API_PREFIX}/project/context", "/api/project/context"}:
            action = "context.read"
        elif path in {f"{API_PREFIX}/project/task-audit", "/api/project/task-audit"}:
            action = "task.audit.read"
        elif method in {"GET", "HEAD"}:
            action = "task.read"
        else:
            action = "task.mutate"

        authorization = request.headers.get("Authorization", "").strip()
        browser_secret = request.cookies.get("devcore_session") if not authorization else None

        if not authorization.startswith("Bearer ") and not browser_secret:
            return build_error_response(
                request=request,
                status_code=401,
                code="individual_credential_required",
                message="Individual credential required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        identity_path = resolve_identity_store_path()
        postgres_identity_dsn = resolve_postgres_identity_dsn()
        if postgres_identity_dsn:
            identity_path = None
        elif not identity_path or not identity_path.is_file():
            return build_error_response(
                request=request,
                status_code=503,
                code="identity_unavailable",
                message="Individual identity store unavailable",
            )

        import asyncio
        from devcore_engine.security.identity import (
            AuthenticationRequired,
            IdentityUnavailable,
            ProjectAccessDenied,
            PostgresIdentityProvider,
            SqliteIdentityProvider,
        )

        try:
            if browser_secret:
                if postgres_identity_dsn:
                    from devcore_engine.security.postgres_browser_sessions import authorize_session
                    identity_source = postgres_identity_dsn
                else:
                    from devcore_engine.security.browser_sessions import authorize_session
                    identity_source = identity_path

                origin = trusted_session_origin(request, allowed_origins, require_origin=method != "GET")
                session = await asyncio.to_thread(
                    authorize_session,
                    identity_source,
                    browser_secret,
                    project,
                    action,
                    origin,
                    csrf=request.headers.get("X-CSRF-Token"),
                    mutate=method != "GET",
                )
                principal = session.principal
                session_id = session.session_id
                request.state.browser_session = session
            else:
                provider = (PostgresIdentityProvider(postgres_identity_dsn)
                            if postgres_identity_dsn else SqliteIdentityProvider(identity_path))
                principal = await asyncio.to_thread(provider.authorize, authorization, project, action)
                session_id = None
        except AuthenticationRequired as exc:
            return build_error_response(
                request=request,
                status_code=401,
                code="invalid_individual_credential",
                message=str(exc) or "Invalid or expired individual credential",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except ProjectAccessDenied as exc:
            return build_error_response(
                request=request,
                status_code=403,
                code="project_access_denied",
                message=str(exc) or "Project action denied",
            )
        except (IdentityUnavailable, sqlite3.Error) as exc:
            return build_error_response(
                request=request,
                status_code=503,
                code="identity_unavailable",
                message="Individual identity store unavailable",
            )

        request.state.principal = principal
        request.state.session_id = session_id
        from devcore_engine.context import RequestContext

        request.state.request_context = RequestContext(
            project_id=project,
            user_id=principal.user_id,
            session_id=session_id,
            trace_id=get_trace_id(request),
        )

        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.middleware("http")
    async def cockpit_login_redirect(request: Request, call_next):
        response = await call_next(request)
        if (request.method == "GET" and request.url.path in COCKPIT_PATHS
                and response.status_code in {401, 403}):
            project = request.query_params.get("project", "")
            target = request.url.path + "?" + request.url.query
            return RedirectResponse("/login?" + urlencode({"project": project, "next": target}),
                                    status_code=303, headers={"Cache-Control": "no-store"})
        return response

    @app.post(f"{API_PREFIX}/llm/gemini", tags=["llm"])
    async def project_gemini(request: Request) -> dict:
        """Generate through the loopback auxiliary route for an authorized project."""
        from devcore_engine.services.postgres_llm_usage import PostgresLlmUsageStore

        principal = getattr(request.state, "principal", None)
        project = getattr(request.state, "authorized_project", None)
        if principal is None or principal.project_id != project:
            raise HTTPException(status_code=403, detail="Project access denied")
        payload = await request.json()
        if not isinstance(payload, dict) or payload.get("project") != project:
            raise HTTPException(status_code=400, detail="Project mismatch")
        dsn = os.environ.get("DEVCORE_DATABASE_URL", "").strip()
        if not dsn or os.environ.get("DEVCORE_TASK_READ_MODE", "").lower() != "postgres":
            raise HTTPException(status_code=503, detail="Project usage store unavailable")
        store = PostgresLlmUsageStore(dsn)
        try:
            await asyncio.to_thread(store.assert_ready, principal)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Project usage store unavailable") from exc
        try:
            return await generate_project_summary(
                principal, payload.get("prompt"), store)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except GeminiRouteUnavailable as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.get(f"{API_PREFIX}/health", response_model=HealthResponse, tags=["health"])
    async def health(request: Request) -> HealthResponse:
        return HealthResponse(trace_id=get_trace_id(request))

    @app.get(f"{API_PREFIX}/contracts", response_model=ContractCatalog, tags=["contracts"])
    async def contracts() -> ContractCatalog:
        return build_contract_catalog()

    @app.get(f"{API_PREFIX}/tasks", response_model=TaskListResponse, tags=["tasks"])
    def list_tasks(
        request: Request,
        project: str,
        status: str | None = None,
        limit: int | None = Query(default=None, ge=1),
        offset: int = Query(default=0, ge=0),
    ) -> TaskListResponse:
        try:
            project = validate_project_id(project)
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
        except TaskBoardInvalid as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "invalid_task_board", "message": str(exc), "details": {"project": project}},
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

        if status is not None:
            norm_status = normalize_status_filter(status)
            tasks = [t for t in tasks if t.status == norm_status]

        total_count = len(tasks)
        if offset > 0 or limit is not None:
            end = offset + limit if limit is not None else None
            paged_tasks = tasks[offset:end]
            has_more = (offset + len(paged_tasks)) < total_count
            return TaskListResponse(
                project=project,
                tasks=paged_tasks,
                total_count=total_count,
                offset=offset,
                limit=limit,
                has_more=has_more,
            )

        return TaskListResponse(
            project=project,
            tasks=tasks,
            total_count=total_count,
            offset=0,
            limit=None,
            has_more=False,
        )

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
    def list_workflows(project: str) -> WorkflowListResponse:
        try:
            project = validate_project_id(project)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": "invalid_project", "message": str(exc)}) from exc
        data_root = default_data_root()
        workflows_dir = data_root / "Workflows"
        workflows = []
        if workflows_dir.exists():
            for state_file in workflows_dir.glob("*.state.json"):
                workflow = load_project_workflow(state_file, project)
                if workflow is not None:
                    workflows.append(workflow)
        return WorkflowListResponse(workflows=workflows)

    @app.get(f"{API_PREFIX}/workflows/{{run_id}}", response_model=WorkflowRunDetail, tags=["workflows"])
    def get_workflow(run_id: str, request: Request, project: str) -> WorkflowRunDetail:
        try:
            project = validate_project_id(project)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": "invalid_project", "message": str(exc)}) from exc
        if not SAFE_RUN_ID.fullmatch(run_id) or ".." in run_id:
            raise HTTPException(status_code=400, detail={"code": "invalid_run_id", "message": "Invalid workflow run id"})
        data_root = default_data_root()
        state_file = data_root / "Workflows" / f"{run_id}.state.json"
        workflow = load_project_workflow(state_file, project)
        if workflow is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "workflow_not_found",
                    "message": f"Workflow run {run_id} not found",
                    "details": {"run_id": run_id},
                },
            )
        return workflow

    def _to_run_response(rec: RunRecord) -> RunDetailResponse:
        return RunDetailResponse(
            run_id=rec.id,
            project_id=rec.project_id,
            task_id=rec.task_id,
            title=rec.title,
            status=rec.status,
            command=rec.command,
            timeout_seconds=rec.timeout_seconds,
            attempt_number=rec.attempt_number,
            max_attempts=rec.max_attempts,
            worker_token=rec.worker_token,
            heartbeat_at=rec.heartbeat_at.isoformat() if rec.heartbeat_at else None,
            cancellation_requested=rec.cancellation_requested,
            output=rec.output,
            error=rec.error,
            exit_code=rec.exit_code,
            idempotency_key=rec.idempotency_key,
            actor=rec.actor,
            created_at=rec.created_at.isoformat(),
            started_at=rec.started_at.isoformat() if rec.started_at else None,
            finished_at=rec.finished_at.isoformat() if rec.finished_at else None,
            tracking_url=f"{API_PREFIX}/runs/{rec.id}",
        )

    @app.post(
        f"{API_PREFIX}/runs",
        response_model=RunDetailResponse,
        status_code=202,
        tags=["runs"],
    )
    def submit_run(
        body: RunSubmissionRequest,
        request: Request,
        response: Response,
        background_tasks: BackgroundTasks,
    ) -> RunDetailResponse:
        engine = get_run_engine()
        authorized_project = getattr(request.state, "authorized_project", None)
        if authorized_project and body.project_id != authorized_project:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "project_mismatch",
                    "message": f"Body project_id '{body.project_id}' does not match authorized project '{authorized_project}'",
                },
            )
        project_id = authorized_project or body.project_id
        idemp_header = request.headers.get("Idempotency-Key")
        idempotency_key = idemp_header or body.idempotency_key
        actor = "system"
        principal = getattr(request.state, "principal", None)
        if principal and getattr(principal, "user_id", None):
            actor = principal.user_id

        submission = RunSubmission(
            project_id=project_id,
            title=body.title,
            command=body.command,
            task_id=body.task_id,
            timeout_seconds=body.timeout_seconds,
            env=body.env,
            idempotency_key=idempotency_key,
            actor=actor,
            metadata=body.metadata,
        )

        try:
            record, created = engine.submit_run(submission)
        except RunBackpressureError as exc:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "queue_backpressure_exceeded",
                    "message": str(exc),
                },
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "invalid_arguments",
                    "message": str(exc),
                },
            ) from exc

        # Signal background worker to execute runs
        engine.wake_worker()

        tracking_url = f"{API_PREFIX}/runs/{record.id}"
        response.headers["Location"] = tracking_url
        return _to_run_response(record)

    @app.post(
        f"{API_PREFIX}/runs/step",
        response_model=RunDetailResponse | None,
        tags=["runs"],
    )
    def step_run(request: Request, project: str | None = None) -> RunDetailResponse | None:
        authorized_project = getattr(request.state, "authorized_project", None) or project
        engine = get_run_engine()
        record = engine.step(project_id=authorized_project)
        if record is None:
            return None
        return _to_run_response(record)


    @app.get(
        f"{API_PREFIX}/runs",
        response_model=RunListResponse,
        tags=["runs"],
    )
    def list_runs(
        project: str,
        status: str | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> RunListResponse:
        try:
            project = validate_project_id(project)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": "invalid_project", "message": str(exc)}) from exc

        engine = get_run_engine()
        records, total = engine.list_runs(project_id=project, status=status, limit=limit, offset=offset)
        return RunListResponse(
            total_count=total,
            runs=[_to_run_response(r) for r in records],
        )

    @app.get(
        f"{API_PREFIX}/runs/{{run_id}}",
        response_model=RunDetailResponse,
        tags=["runs"],
    )
    def get_run(run_id: str, project: str) -> RunDetailResponse:
        try:
            project = validate_project_id(project)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": "invalid_project", "message": str(exc)}) from exc

        engine = get_run_engine()
        record = engine.get_run(run_id)
        if record is None or record.project_id != project:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "run_not_found",
                    "message": f"Run {run_id} not found in project {project}",
                },
            )
        return _to_run_response(record)

    @app.post(
        f"{API_PREFIX}/runs/{{run_id}}/cancel",
        response_model=RunDetailResponse,
        tags=["runs"],
    )
    def cancel_run(run_id: str, project: str) -> RunDetailResponse:
        try:
            project = validate_project_id(project)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": "invalid_project", "message": str(exc)}) from exc

        engine = get_run_engine()
        record = engine.get_run(run_id)
        if record is None or record.project_id != project:
            raise HTTPException(
                status_code=404,
                detail={"code": "run_not_found", "message": f"Run {run_id} not found"},
            )
        updated = engine.cancel_run(run_id)
        return _to_run_response(updated)

    @app.post(
        f"{API_PREFIX}/runs/{{run_id}}/pause",
        response_model=RunDetailResponse,
        tags=["runs"],
    )
    def pause_run(run_id: str, project: str) -> RunDetailResponse:
        try:
            project = validate_project_id(project)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": "invalid_project", "message": str(exc)}) from exc

        engine = get_run_engine()
        record = engine.get_run(run_id)
        if record is None or record.project_id != project:
            raise HTTPException(
                status_code=404,
                detail={"code": "run_not_found", "message": f"Run {run_id} not found"},
            )
        try:
            updated = engine.pause_run(run_id)
        except RunTransitionError as exc:
            raise HTTPException(status_code=400, detail={"code": "invalid_transition", "message": str(exc)}) from exc
        return _to_run_response(updated)

    @app.post(
        f"{API_PREFIX}/runs/{{run_id}}/resume",
        response_model=RunDetailResponse,
        tags=["runs"],
    )
    def resume_run(run_id: str, project: str) -> RunDetailResponse:
        try:
            project = validate_project_id(project)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": "invalid_project", "message": str(exc)}) from exc

        engine = get_run_engine()
        record = engine.get_run(run_id)
        if record is None or record.project_id != project:
            raise HTTPException(
                status_code=404,
                detail={"code": "run_not_found", "message": f"Run {run_id} not found"},
            )
        try:
            updated = engine.resume_run(run_id)
        except RunTransitionError as exc:
            raise HTTPException(status_code=400, detail={"code": "invalid_transition", "message": str(exc)}) from exc
        return _to_run_response(updated)

    @app.post(
        f"{API_PREFIX}/runs/{{run_id}}/approve",
        response_model=RunDetailResponse,
        tags=["runs"],
    )
    def approve_run(run_id: str, project: str) -> RunDetailResponse:
        try:
            project = validate_project_id(project)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": "invalid_project", "message": str(exc)}) from exc

        engine = get_run_engine()
        record = engine.get_run(run_id)
        if record is None or record.project_id != project:
            raise HTTPException(
                status_code=404,
                detail={"code": "run_not_found", "message": f"Run {run_id} not found"},
            )
        try:
            updated = engine.approve_run(run_id)
        except RunTransitionError as exc:
            raise HTTPException(status_code=400, detail={"code": "invalid_transition", "message": str(exc)}) from exc
        return _to_run_response(updated)

    @app.get(f"{API_PREFIX}/routes", response_model=RouteCatalogResponse, tags=["routes"])
    def list_routes() -> RouteCatalogResponse:
        routes_list: list[RouteInfo] = []
        for r in app.routes:
            if hasattr(r, "methods") and hasattr(r, "path"):
                methods = sorted(list(r.methods - {"HEAD", "OPTIONS"}))
                if not methods:
                    continue
                routes_list.append(
                    RouteInfo(
                        path=r.path,
                        methods=methods,
                        name=getattr(r, "name", ""),
                        tags=list(getattr(r, "tags", [])),
                        deprecated=bool(getattr(r, "deprecated", False)),
                        description=getattr(r, "description", None),
                    )
                )
        return RouteCatalogResponse(
            total_routes=len(routes_list),
            routes=sorted(routes_list, key=lambda x: (x.path, x.methods[0] if x.methods else "")),
        )

    # Legacy facades (conservées temporairement comme façades documentées)
    @app.get(
        "/api/tasks",
        response_model=TaskListResponse,
        tags=["legacy_facades"],
        deprecated=True,
        description="Legacy facade forwarding to /api/v1/tasks",
    )
    def legacy_list_tasks(
        request: Request,
        project: str,
        status: str | None = None,
        limit: int | None = Query(default=None, ge=1),
        offset: int = Query(default=0, ge=0),
    ) -> TaskListResponse:
        return list_tasks(request, project=project, status=status, limit=limit, offset=offset)

    @app.get(
        "/api/health",
        response_model=HealthResponse,
        tags=["legacy_facades"],
        deprecated=True,
        description="Legacy facade forwarding to /api/v1/health",
    )
    async def legacy_health(request: Request) -> HealthResponse:
        return await health(request)

    @app.get(
        "/api/contracts",
        response_model=ContractCatalog,
        tags=["legacy_facades"],
        deprecated=True,
        description="Legacy facade forwarding to /api/v1/contracts",
    )
    async def legacy_contracts() -> ContractCatalog:
        return await contracts()

    @app.get(
        "/api/routes",
        response_model=RouteCatalogResponse,
        tags=["legacy_facades"],
        deprecated=True,
        description="Legacy facade forwarding to /api/v1/routes",
    )
    def legacy_routes() -> RouteCatalogResponse:
        return list_routes()

    @app.get(
        "/api/workflows",
        response_model=WorkflowListResponse,
        tags=["legacy_facades"],
        deprecated=True,
        description="Legacy facade forwarding to /api/v1/workflows",
    )
    def legacy_list_workflows(project: str) -> WorkflowListResponse:
        return list_workflows(project=project)

    @app.get(
        "/api/workflows/{run_id}",
        response_model=WorkflowRunDetail,
        tags=["legacy_facades"],
        deprecated=True,
        description="Legacy facade forwarding to /api/v1/workflows/{run_id}",
    )
    def legacy_get_workflow(run_id: str, request: Request, project: str) -> WorkflowRunDetail:
        return get_workflow(run_id=run_id, request=request, project=project)

    @app.post(f"{API_PREFIX}/tasks/done", tags=["tasks"])
    @app.post("/api/done", tags=["legacy_facades"], deprecated=True)
    async def complete_task_endpoint(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            data = {}
        authorized_project = getattr(request.state, "authorized_project", None)
        body_project = data.get("project")
        if body_project and authorized_project and body_project != authorized_project:
            return build_error_response(
                request=request,
                status_code=400,
                code="project_mismatch",
                message=f"Body project '{body_project}' does not match authorized project '{authorized_project}'",
            )
        project = authorized_project or body_project
        task_id = data.get("id") or data.get("task_id")
        expected_version = data.get("expected_version")
        if not project or not task_id:
            return build_error_response(request=request, status_code=400, code="invalid_arguments",
                                        message="project and task_id required")
        context = getattr(request.state, "request_context", None)
        try:
            team_store = team_task_mutations()
            if team_store is not None:
                success, msg = team_store.transition(project, task_id, "complete", expected_version, context)
            else:
                db_path = resolve_api_db_path(task_repository)
                success, msg = complete_task_usecase(project, task_id, expected_version, context=context, db_path=db_path)
            if not success:
                return build_error_response(request=request, status_code=404, code="task_not_found", message=msg)
            return JSONResponse(status_code=200, content={"status": "success", "message": msg, "project": project, "task_id": task_id})
        except TaskMutationConflict as exc:
            return build_error_response(request=request, status_code=409, code=exc.code, message=str(exc))
        except Exception as exc:
            return build_error_response(request=request, status_code=400, code="mutation_failed", message=str(exc))

    @app.post(f"{API_PREFIX}/tasks/pause", tags=["tasks"])
    @app.post("/api/pause", tags=["legacy_facades"], deprecated=True)
    async def pause_task_endpoint(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            data = {}
        authorized_project = getattr(request.state, "authorized_project", None)
        body_project = data.get("project")
        if body_project and authorized_project and body_project != authorized_project:
            return build_error_response(
                request=request,
                status_code=400,
                code="project_mismatch",
                message=f"Body project '{body_project}' does not match authorized project '{authorized_project}'",
            )
        project = authorized_project or body_project
        task_id = data.get("id") or data.get("task_id")
        expected_version = data.get("expected_version")
        if not project or not task_id:
            return build_error_response(request=request, status_code=400, code="invalid_arguments",
                                        message="project and task_id required")
        context = getattr(request.state, "request_context", None)
        try:
            team_store = team_task_mutations()
            if team_store is not None:
                ok, _ = team_store.transition(project, task_id, "pause", expected_version, context)
            else:
                db_path = resolve_api_db_path(task_repository)
                ok = transition_task_usecase(project, task_id, "pause", expected_version, context=context, db_path=db_path)
            if not ok:
                return build_error_response(request=request, status_code=404, code="task_not_found", message="Task not found")
            return JSONResponse(status_code=200, content={"status": "success", "message": f"Task {task_id} paused", "project": project, "task_id": task_id})
        except TaskMutationConflict as exc:
            return build_error_response(request=request, status_code=409, code=exc.code, message=str(exc))
        except Exception as exc:
            return build_error_response(request=request, status_code=400, code="mutation_failed", message=str(exc))

    @app.post(f"{API_PREFIX}/tasks/resume", tags=["tasks"])
    @app.post("/api/resume", tags=["legacy_facades"], deprecated=True)
    async def resume_task_endpoint(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            data = {}
        authorized_project = getattr(request.state, "authorized_project", None)
        body_project = data.get("project")
        if body_project and authorized_project and body_project != authorized_project:
            return build_error_response(
                request=request,
                status_code=400,
                code="project_mismatch",
                message=f"Body project '{body_project}' does not match authorized project '{authorized_project}'",
            )
        project = authorized_project or body_project
        task_id = data.get("id") or data.get("task_id")
        expected_version = data.get("expected_version")
        if not project or not task_id:
            return build_error_response(request=request, status_code=400, code="invalid_arguments",
                                        message="project and task_id required")
        context = getattr(request.state, "request_context", None)
        try:
            team_store = team_task_mutations()
            if team_store is not None:
                ok, _ = team_store.transition(project, task_id, "resume", expected_version, context)
            else:
                db_path = resolve_api_db_path(task_repository)
                ok = transition_task_usecase(project, task_id, "resume", expected_version, context=context, db_path=db_path)
            if not ok:
                return build_error_response(request=request, status_code=404, code="task_not_found", message="Task not found")
            return JSONResponse(status_code=200, content={"status": "success", "message": f"Task {task_id} resumed", "project": project, "task_id": task_id})
        except TaskMutationConflict as exc:
            return build_error_response(request=request, status_code=409, code=exc.code, message=str(exc))
        except Exception as exc:
            return build_error_response(request=request, status_code=400, code="mutation_failed", message=str(exc))

    @app.delete(f"{API_PREFIX}/tasks/delete", tags=["tasks"])
    @app.delete("/api/delete", tags=["legacy_facades"], deprecated=True)
    async def delete_task_endpoint(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            data = {}
        authorized_project = getattr(request.state, "authorized_project", None)
        body_project = data.get("project")
        if body_project and authorized_project and body_project != authorized_project:
            return build_error_response(
                request=request,
                status_code=400,
                code="project_mismatch",
                message=f"Body project '{body_project}' does not match authorized project '{authorized_project}'",
            )
        project = authorized_project or body_project
        task_id = data.get("id") or data.get("task_id")
        expected_version = data.get("expected_version")
        if not project or not task_id:
            return build_error_response(request=request, status_code=400, code="invalid_arguments",
                                        message="project and task_id required")
        context = getattr(request.state, "request_context", None)
        try:
            team_store = team_task_mutations()
            if team_store is not None:
                ok, _ = team_store.transition(project, task_id, "delete", expected_version, context)
            else:
                db_path = resolve_api_db_path(task_repository)
                ok, _ = delete_task_usecase(project, task_id, expected_version, context=context, db_path=db_path)
            if not ok:
                return build_error_response(request=request, status_code=404, code="task_not_found", message="Task not found")
            return JSONResponse(status_code=200, content={"status": "success", "message": f"Task {task_id} deleted", "project": project, "task_id": task_id})
        except TaskMutationConflict as exc:
            return build_error_response(request=request, status_code=409, code=exc.code, message=str(exc))
        except Exception as exc:
            return build_error_response(request=request, status_code=400, code="mutation_failed", message=str(exc))

    @app.post(f"{API_PREFIX}/tasks/next", tags=["tasks"])
    async def next_task_endpoint(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            data = {}
        authorized_project = getattr(request.state, "authorized_project", None)
        body_project = data.get("project")
        if body_project and authorized_project and body_project != authorized_project:
            return build_error_response(
                request=request,
                status_code=400,
                code="project_mismatch",
                message=f"Body project '{body_project}' does not match authorized project '{authorized_project}'",
            )
        project = authorized_project or body_project
        if not project:
            return build_error_response(request=request, status_code=400, code="invalid_arguments", message="project required")
        team_store = team_task_mutations()
        if team_store is not None:
            try:
                active = team_store.next_task(project, getattr(request.state, "request_context", None))
            except TaskMutationConflict as exc:
                return build_error_response(request=request, status_code=409, code=exc.code, message=str(exc))
            return JSONResponse(status_code=200, content={"status": "success", "task": active})
        db_path = resolve_api_db_path(task_repository)
        if not db_path or not db_path.is_file():
            return build_error_response(request=request, status_code=404, code="database_not_found", message="Task database not found")
        from devcore_engine.services.tasks import TaskService
        with closing(sqlite3.connect(str(db_path), timeout=30.0)) as conn:
            conn.row_factory = sqlite3.Row
            service = TaskService(conn)
            active = service.next_task(project)
        return JSONResponse(status_code=200, content={"status": "success", "task": active})

    @app.post(f"{API_PREFIX}/tasks", tags=["tasks"])
    async def create_task_endpoint(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:
            data = {}
        authorized_project = getattr(request.state, "authorized_project", None)
        body_project = data.get("project")
        if body_project and authorized_project and body_project != authorized_project:
            return build_error_response(
                request=request,
                status_code=400,
                code="project_mismatch",
                message=f"Body project '{body_project}' does not match authorized project '{authorized_project}'",
            )
        project = authorized_project or body_project
        title = data.get("title")
        mode = data.get("mode", "coding")
        steps = data.get("steps", 1)
        depends_on = data.get("depends_on")
        if not project or not title:
            return build_error_response(request=request, status_code=400, code="invalid_arguments", message="project and title required")
        team_store = team_task_mutations()
        if team_store is not None:
            try:
                created = team_store.create(
                    project, title, mode, steps, depends_on,
                    getattr(request.state, "request_context", None),
                )
            except TaskMutationConflict as exc:
                return build_error_response(request=request, status_code=409, code=exc.code, message=str(exc))
            except ValueError as exc:
                return build_error_response(request=request, status_code=400, code="invalid_arguments", message=str(exc))
            return JSONResponse(status_code=201, content={"status": "success", "task": created})
        db_path = resolve_api_db_path(task_repository)
        if not db_path or not db_path.is_file():
            return build_error_response(request=request, status_code=404, code="database_not_found", message="Task database not found")
        from devcore_engine.services.tasks import TaskService
        with closing(sqlite3.connect(str(db_path), timeout=30.0)) as conn:
            conn.row_factory = sqlite3.Row
            service = TaskService(conn)
            created = service.add_task(title, mode=mode, steps=steps, project_id=project, depends_on=depends_on)
        return JSONResponse(status_code=201, content={"status": "success", "task": created})

    @app.get(
        "/api/dashboard/tasks",
        tags=["legacy_facades"],
        deprecated=True,
        description="Legacy facade matching Cockpit / Individual task list shape",
    )
    def legacy_dashboard_tasks(
        request: Request,
        project: str,
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> JSONResponse:
        response = list_tasks(request, project=project, limit=limit, offset=offset)
        tasks_list = [
            {
                "id": t.id,
                "project": t.project,
                "title": t.title,
                "status": canonical_db_status(t.status),
                "version": t.version,
            }
            for t in response.tasks
        ]
        return JSONResponse(status_code=200, content=tasks_list)

    def team_dashboard_snapshot(request: Request, project: str, task_offset: int = 0) -> dict | JSONResponse:
        if team_project_reader() is None:
            return build_error_response(request=request, status_code=503,
                                        code="team_dashboard_unavailable",
                                        message="PostgreSQL team dashboard required")
        principal = getattr(request.state, "principal", None)
        if principal is None:
            return build_error_response(request=request, status_code=401,
                                        code="individual_credential_required",
                                        message="Individual credential required")
        if principal.project_id != project:
            return build_error_response(request=request, status_code=403,
                                        code="project_access_denied",
                                        message="Project action denied")
        dsn = os.environ.get("DEVCORE_DATABASE_URL", "").strip()
        return PostgresDashboardProjection(dsn).snapshot(principal, task_offset=task_offset)

    @app.get("/api/dashboard", tags=["projects"])
    @app.get(f"{API_PREFIX}/projects/dashboard", tags=["projects"])
    def postgres_dashboard(request: Request, project: str,
                           task_offset: int = Query(default=0, ge=0, le=100000)) -> JSONResponse:
        snapshot = team_dashboard_snapshot(request, project, task_offset)
        return snapshot if isinstance(snapshot, JSONResponse) else JSONResponse(status_code=200, content=snapshot)

    @app.get("/login", tags=["projects"])
    def postgres_login(project: str, next: str = "") -> HTMLResponse:
        project = validate_project_id(project)
        if team_project_reader() is None:
            raise HTTPException(status_code=503, detail="PostgreSQL team dashboard required")
        return HTMLResponse(render_team_login(project, next), headers={"Cache-Control": "no-store"})

    @app.get("/cockpit", tags=["projects"])
    @app.get("/cockpit/terminal", tags=["projects"])
    @app.get("/index.html", tags=["projects"])
    @app.get("/index_terminal.html", tags=["projects"])
    def postgres_cockpit(request: Request, project: str,
                         task_offset: int = Query(default=0, ge=0, le=100000)) -> Response:
        snapshot = team_dashboard_snapshot(request, project, task_offset)
        if isinstance(snapshot, JSONResponse):
            return snapshot
        page = render_team_cockpit(
            DEVCORE_BASE / "Dashboard", snapshot,
            terminal=request.url.path.endswith("/terminal") or request.url.path == "/index_terminal.html",
            user_id=request.state.principal.user_id,
        )
        return HTMLResponse(page, headers={"Cache-Control": "no-store"})

    @app.get(f"{API_PREFIX}/project/context", tags=["projects"])
    @app.get("/api/project/context", tags=["legacy_facades"], deprecated=True)
    def get_project_context_endpoint(
        request: Request,
        project: str,
        budget_bytes: int | None = Query(default=None, ge=256, le=65536),
        query: str = Query(default="", max_length=4096),
    ) -> Response:
        from devcore_engine.security.identity import CONTEXT_READ
        from devcore_engine.services.project_context import ContextBudgetExceeded, encode_context
        from devcore_engine.services.registered_project_context import (
            ProjectContextUnavailable, load_registered_project_context,
        )
        principal = getattr(request.state, "principal", None)
        enforced = require_auth if require_auth is not None else is_auth_enforced()
        if enforced and (
            principal is None or principal.project_id != project or principal.action != CONTEXT_READ
        ):
            raise HTTPException(status_code=403, detail="Individual context admission required")
        max_bytes = int(os.environ.get("DEVCORE_HTTP_CONTEXT_MAX_BYTES", "12000"))
        budget = max_bytes if budget_bytes is None else budget_bytes
        if budget > max_bytes:
            raise HTTPException(status_code=422, detail="Requested budget exceeds server context limit")
        try:
            team_reader = team_project_reader()
            if team_reader is not None:
                result = team_reader.context(principal, budget_bytes=budget, query=query)
            else:
                db_path = resolve_api_db_path(task_repository)
                if not db_path or not db_path.is_file():
                    raise ProjectContextUnavailable("Registered project context unavailable")
                result = load_registered_project_context(
                    db_path, principal, budget_bytes=budget, query=query
                )
        except ContextBudgetExceeded as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        except ProjectContextUnavailable as exc:
            raise HTTPException(status_code=503, detail="Registered project context unavailable") from exc
        return Response(
            content=(encode_context(result) + "\n").encode("utf-8"),
            media_type="application/json",
            headers={"Cache-Control": "no-store"},
        )

    @app.get(f"{API_PREFIX}/project/task-audit", tags=["projects"])
    @app.get("/api/project/task-audit", tags=["legacy_facades"], deprecated=True)
    async def get_task_audit_endpoint(
        request: Request,
        project: str,
        limit: int = Query(default=20, ge=1, le=100),
        before_id: str | None = None,
        task_id: str | None = None,
    ) -> Response:
        import asyncio
        from devcore_engine.security.identity import AUDIT_READ
        from devcore_engine.services.project_context import encode_context
        from devcore_engine.services.task_audit import (
            InvalidAuditCursor, TaskAuditUnavailable, read_task_audit,
        )
        principal = getattr(request.state, "principal", None)
        enforced = require_auth if require_auth is not None else is_auth_enforced()
        if enforced and (
            principal is None or principal.project_id != project or principal.action != AUDIT_READ
        ):
            raise HTTPException(status_code=403, detail="Individual task audit admission required")
        try:
            team_reader = team_project_reader()
            if team_reader is not None:
                result = await asyncio.to_thread(
                    team_reader.task_audit, principal, limit=limit,
                    before_id=before_id, task_id=task_id,
                )
            else:
                db_path = resolve_api_db_path(task_repository)
                if not db_path or not db_path.is_file():
                    raise TaskAuditUnavailable("Task audit database unavailable")
                result = await asyncio.to_thread(
                    read_task_audit, db_path, principal, limit=limit,
                    before_id=before_id, task_id=task_id,
                )
        except (InvalidAuditCursor, ValueError):
            raise HTTPException(status_code=400, detail={"code": "invalid_audit_arguments", "message": "Invalid scoped audit arguments"})
        except TaskAuditUnavailable:
            raise HTTPException(status_code=503, detail={"code": "task_audit_unavailable", "message": "Qualified task audit unavailable"})
        return Response(
            content=(encode_context(result) + "\n").encode("utf-8"),
            media_type="application/json",
            headers={"Cache-Control": "no-store"},
        )

    @app.get(f"{API_PREFIX}/projects/events/stream", tags=["projects"])
    @app.get("/api/dashboard/stream", tags=["legacy_facades"], deprecated=True)
    async def project_events_stream(request: Request, project: str) -> StreamingResponse:
        from devcore_engine.security.identity import PostgresIdentityProvider

        if not (require_auth if require_auth is not None else is_auth_enforced()):
            raise HTTPException(status_code=403, detail="Individual admission required")
        principal = getattr(request.state, "principal", None)
        if principal is None or principal.project_id != project or principal.action != "task.read":
            raise HTTPException(status_code=403, detail="Project read admission required")
        dsn = resolve_postgres_identity_dsn()
        if not dsn or team_project_reader() is None:
            raise HTTPException(status_code=503, detail="Project event stream unavailable")
        try:
            after_id = validate_event_cursor(request.headers.get("Last-Event-ID"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        reader = PostgresProjectEventReader(dsn)
        stream_lifetime = max(2, min(120, int(os.environ.get("DEVCORE_PROJECT_STREAM_MAX_SECONDS", "120"))))
        authorization = request.headers.get("Authorization", "").strip()
        secret = request.cookies.get("devcore_session") if not authorization else None
        origin = trusted_session_origin(request, allowed_origins)
        try:
            await asyncio.wait_for(project_stream_slots.acquire(), timeout=0.02)
        except TimeoutError as exc:
            raise HTTPException(status_code=503, detail="Stream capacity reached",
                                headers={"Retry-After": "5"}) from exc

        async def credential_still_valid() -> bool:
            try:
                if authorization:
                    admitted = await asyncio.to_thread(
                        PostgresIdentityProvider(dsn).authorize,
                        authorization, project, "task.read",
                    )
                else:
                    from devcore_engine.security.postgres_browser_sessions import authorize_session
                    session = await asyncio.to_thread(
                        authorize_session, dsn, secret, project, "task.read", origin,
                        mutate=False,
                    )
                    admitted = session.principal
                return admitted.user_id == principal.user_id
            except Exception:
                return False

        async def frames():
            cursor = after_id
            elapsed = 0
            last_resync_cursor = object()
            shutdown_event = getattr(request.app.state, "managed_shutdown_event", None)
            try:
                while (elapsed < stream_lifetime
                       and (shutdown_event is None or not shutdown_event.is_set())
                       and not await request.is_disconnected()):
                    if not await credential_still_valid():
                        break
                    ids, cursor, resync = await asyncio.to_thread(reader.changes, project, cursor)
                    sent = False
                    if resync and cursor != last_resync_cursor:
                        payload = json.dumps({"schema_version": 1, "has_changes": True,
                                              "snapshot_required": True}, separators=(",", ":"))
                        yield f"event: dashboard.delta\ndata: {payload}\n"
                        if cursor:
                            yield f"id: {cursor}\n"
                        yield "\n"
                        last_resync_cursor = cursor
                        sent = True
                    else:
                        for event_id in ids:
                            yield ("event: dashboard.delta\n"
                                   "data: {\"schema_version\":1,\"has_changes\":true}\n"
                                   f"id: {event_id}\n\n")
                    if not ids and not sent:
                        yield ": heartbeat\n\n"
                    await asyncio.sleep(2)
                    elapsed += 2
            finally:
                project_stream_slots.release()

        return StreamingResponse(frames(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    @app.api_route(f"{API_PREFIX}/auth/session", methods=["GET", "POST", "DELETE"], tags=["auth"])
    @app.api_route("/api/auth/session", methods=["GET", "POST", "DELETE"], tags=["legacy_facades"], deprecated=True)
    async def browser_session_route(request: Request) -> Response:
        from devcore_engine.security.identity import AuthenticationRequired, IdentityUnavailable, ProjectAccessDenied
        from devcore_engine.security.browser_sessions import (
            COOKIE, csrf_for_session,
        )
        import asyncio
        origin = trusted_session_origin(request, allowed_origins, require_origin=request.method != "GET")
        identity_path = resolve_identity_store_path()
        postgres_identity_dsn = resolve_postgres_identity_dsn()
        if (not identity_path or not identity_path.is_file()) and not postgres_identity_dsn:
            return build_error_response(request=request, status_code=503, code="identity_unavailable", message="Individual identity store unavailable")
        secret = request.cookies.get(COOKIE)
        try:
            if request.method == "POST":
                body = await request.body()
                if len(body) > 1024 * 1024:
                    return build_error_response(request=request, status_code=413, code="request_too_large", message="Request body too large")
                data = json.loads(body)
                if not isinstance(data, dict):
                    return build_error_response(request=request, status_code=400, code="invalid_arguments", message="JSON object required")
                project = validate_project_id(data.get("project"))
                authorization = request.headers.get("Authorization")
                if authorization:
                    if "user_id" in data or "password" in data:
                        return build_error_response(request=request, status_code=400, code="invalid_arguments", message="Mixed authentication methods")
                    if postgres_identity_dsn:
                        from devcore_engine.security.postgres_browser_sessions import create_session
                        session, secret = await asyncio.to_thread(
                            create_session, postgres_identity_dsn, authorization, project, origin, previous=secret,
                        )
                    else:
                        from devcore_engine.security.browser_sessions import create_session
                        session, secret = await asyncio.to_thread(
                            create_session, identity_path, authorization, project, origin, previous=secret,
                        )
                else:
                    if postgres_identity_dsn:
                        from devcore_engine.security.postgres_password_sessions import create_password_session
                        user_id = validate_project_id(data.get("user_id"))
                        session, secret = await asyncio.to_thread(
                            create_password_session, postgres_identity_dsn, user_id, data.get("password"), project, origin, previous=secret,
                        )
                    else:
                        from devcore_engine.security.passwords import create_password_session, LoginBusy
                        user_id = validate_project_id(data.get("user_id"))
                        try:
                            session, secret = await asyncio.to_thread(
                                create_password_session, identity_path, user_id, data.get("password"), project, origin, previous=secret,
                            )
                        except LoginBusy:
                            raise HTTPException(status_code=429, detail="Login capacity reached", headers={"Retry-After": "1"})
            else:
                if postgres_identity_dsn:
                    from devcore_engine.security.postgres_browser_sessions import session_info, authorize_session, revoke_session
                    session = await asyncio.to_thread(session_info, postgres_identity_dsn, secret, origin)
                else:
                    from devcore_engine.security.browser_sessions import session_info, authorize_session, revoke_session
                    session = await asyncio.to_thread(session_info, identity_path, secret, origin)
                if request.method == "DELETE":
                    await asyncio.to_thread(
                        authorize_session, postgres_identity_dsn if postgres_identity_dsn else identity_path, secret, session.project_id, "task.read", origin,
                        csrf=request.headers.get("X-CSRF-Token"), mutate=True,
                    )
                    await asyncio.to_thread(revoke_session, postgres_identity_dsn if postgres_identity_dsn else identity_path, secret)
            content = {
                "user_id": session.principal.user_id,
                "project": session.project_id,
                "expires_at": session.expires_at,
                "csrf_token": csrf_for_session(secret),
                "actions": list(session.actions),
            }
            resp = JSONResponse(
                content={"status": "logged_out"} if request.method == "DELETE" else content,
                headers={"Cache-Control": "no-store"},
            )
            if request.method == "POST":
                resp.set_cookie(
                    COOKIE, secret, max_age=max(0, int(session.expires_at - time.time())),
                    httponly=True, secure=request.url.scheme == "https", samesite="strict", path="/",
                )
            elif request.method == "DELETE":
                resp.delete_cookie(COOKIE, path="/", httponly=True, secure=request.url.scheme == "https", samesite="strict")
            return resp
        except AuthenticationRequired as exc:
            return build_error_response(request=request, status_code=401, code="invalid_credentials", message=str(exc))
        except ProjectAccessDenied as exc:
            return build_error_response(request=request, status_code=403, code="project_access_denied", message=str(exc))
        except (IdentityUnavailable, sqlite3.Error) as exc:
            return build_error_response(request=request, status_code=503, code="identity_unavailable", message=str(exc))
        except (ValueError, TypeError, UnicodeError) as exc:
            return build_error_response(request=request, status_code=400, code="invalid_arguments", message=str(exc))

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
