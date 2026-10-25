from typing import Literal, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    schema_version: Literal[1] = 1
    service: Literal["devcore-api"] = "devcore-api"
    status: Literal["ok"] = "ok"
    api_version: Literal["v1"] = "v1"
    trace_id: str = Field(min_length=1)


class ErrorBody(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    details: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    schema_version: Literal[1] = 1
    error: ErrorBody
    trace_id: str = Field(min_length=1)


class AutomationHookRequest(BaseModel):
    project: str = Field(min_length=1)
    hook: Literal["session_start", "session_end", "git_commit", "tool_use"]
    source: Literal["codex", "claude", "gemini", "git"]
    session: Optional[str] = None
    commit: Optional[str] = None
    tool: Optional[str] = None
    reported_outcome: Optional[Literal["succeeded", "failed"]] = None
    occurrence: Optional[str] = None


class GitScanRequest(BaseModel):
    project: str = Field(min_length=1)
    commit: Optional[str] = None


class ProjectJobRequest(BaseModel):
    project: str = Field(min_length=1)


class DailyMetricsScheduleRequest(BaseModel):
    project: str = Field(min_length=1)
    timezone: str = Field(min_length=1, max_length=80)
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)


class AgentPilotProposalRequest(BaseModel):
    project: Literal["devcore"]
    file: str = Field(min_length=1, max_length=260)
    task: str = Field(min_length=1, max_length=8000)


class AgentPilotApprovalRequest(BaseModel):
    project: Literal["devcore"]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class WorkflowStepState(BaseModel):
    id: str
    status: str
    starts_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    output: Optional[dict] = None


class WorkflowRunDetail(BaseModel):
    run_id: str
    project: str
    name: str
    description: Optional[str] = None
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    step_definitions: list[dict]
    steps: dict[str, WorkflowStepState]


class WorkflowListResponse(BaseModel):
    workflows: list[WorkflowRunDetail]


class RouteInfo(BaseModel):
    path: str
    methods: list[str]
    name: str
    tags: list[str] = Field(default_factory=list)
    deprecated: bool = False
    description: Optional[str] = None


class RouteCatalogResponse(BaseModel):
    schema_version: Literal[1] = 1
    api_version: Literal["v1"] = "v1"
    total_routes: int
    routes: list[RouteInfo]


class RunSubmissionRequest(BaseModel):
    project_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    command: list[str] | str
    task_id: Optional[str] = None
    timeout_seconds: float = Field(default=300.0, ge=1.0)
    env: dict[str, str] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class RunDetailResponse(BaseModel):
    schema_version: Literal[1] = 1
    run_id: str
    project_id: str
    task_id: Optional[str] = None
    title: str
    status: str
    command: list[str]
    timeout_seconds: float
    attempt_number: int
    max_attempts: int
    worker_token: Optional[str] = None
    heartbeat_at: Optional[str] = None
    cancellation_requested: bool = False
    output: Optional[str] = None
    error: Optional[str] = None
    exit_code: Optional[int] = None
    idempotency_key: Optional[str] = None
    actor: str = "system"
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    tracking_url: str


class RunListResponse(BaseModel):
    schema_version: Literal[1] = 1
    total_count: int
    runs: list[RunDetailResponse]

