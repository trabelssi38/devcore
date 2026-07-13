from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


TaskStatus = Literal["todo", "active", "paused", "done", "skipped"]
TaskMode = Literal["reasoning", "coding", "bulk"]
RunStatus = Literal["queued", "running", "paused", "succeeded", "failed", "cancelled", "timed_out"]
HealthStatus = Literal["ok", "degraded", "down"]
WorkspaceStatus = Literal["active", "archived", "suspended"]
UserStatus = Literal["active", "disabled"]
WorkspaceRole = Literal["owner", "admin", "developer", "viewer"]


class UserContract(BaseModel):
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^usr_[a-zA-Z0-9_-]+$")
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    display_name: str = Field(min_length=1)
    status: UserStatus = "active"


class OrganizationContract(BaseModel):
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^org_[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=1)
    status: WorkspaceStatus = "active"


class WorkspaceContract(BaseModel):
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^wks_[a-zA-Z0-9_-]+$")
    organization_id: str = Field(pattern=r"^org_[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=1)
    status: WorkspaceStatus = "active"


class WorkspaceMembershipContract(BaseModel):
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^mem_[a-zA-Z0-9_-]+$")
    workspace_id: str = Field(pattern=r"^wks_[a-zA-Z0-9_-]+$")
    user_id: str = Field(pattern=r"^usr_[a-zA-Z0-9_-]+$")
    role: WorkspaceRole


class WorkspaceQuotaContract(BaseModel):
    schema_version: Literal[1] = 1
    workspace_id: str = Field(pattern=r"^wks_[a-zA-Z0-9_-]+$")
    runs_per_day: int = Field(ge=0)
    model_tokens_per_day: int = Field(ge=0)
    storage_mb: int = Field(ge=0)


class TaskContract(BaseModel):
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^T-\d+$")
    title: str = Field(min_length=1)
    status: TaskStatus
    mode: TaskMode
    steps_done: int = Field(default=0, ge=0)
    steps_total: int = Field(default=1, ge=1)
    project: str | None = None


class RunContract(BaseModel):
    schema_version: Literal[1] = 1
    id: str = Field(min_length=1)
    task_id: str = Field(pattern=r"^T-\d+$")
    status: RunStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    trace_id: str | None = None


class DomainEvent(BaseModel):
    schema_version: Literal[1] = 1
    id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    source: str = Field(min_length=1)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict = Field(default_factory=dict)


class PluginContract(BaseModel):
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    name: str = Field(min_length=1)
    enabled: bool
    version: str | None = None
    capabilities: dict = Field(default_factory=dict)


class HealthContract(BaseModel):
    schema_version: Literal[1] = 1
    status: HealthStatus
    checks: dict = Field(default_factory=dict)


class TaskListResponse(BaseModel):
    schema_version: Literal[1] = 1
    project: str = Field(min_length=1)
    tasks: list[TaskContract]


class ContractCatalog(BaseModel):
    schema_version: Literal[1] = 1
    api_version: Literal["v1"] = "v1"
    contracts: list[
        Literal[
            "Task",
            "Run",
            "Event",
            "Plugin",
            "Health",
            "User",
            "Organization",
            "Workspace",
            "WorkspaceMembership",
            "WorkspaceQuota",
        ]
    ]
    task: TaskContract
    run: RunContract
    event: DomainEvent
    plugin: PluginContract
    health: HealthContract
    user: UserContract
    organization: OrganizationContract
    workspace: WorkspaceContract
    workspace_membership: WorkspaceMembershipContract
    workspace_quota: WorkspaceQuotaContract


def build_contract_catalog() -> ContractCatalog:
    return ContractCatalog(
        contracts=[
            "Task",
            "Run",
            "Event",
            "Plugin",
            "Health",
            "User",
            "Organization",
            "Workspace",
            "WorkspaceMembership",
            "WorkspaceQuota",
        ],
        task=TaskContract(id="T-1", title="Example task", status="todo", mode="coding"),
        run=RunContract(id="run-1", task_id="T-1", status="queued"),
        event=DomainEvent(id="evt-1", type="TaskCreated", source="task_service"),
        plugin=PluginContract(id="python-fastapi", name="Python FastAPI", enabled=True),
        health=HealthContract(status="ok"),
        user=UserContract(id="usr_system", email="system@devcore.local", display_name="System"),
        organization=OrganizationContract(id="org_default", name="Default Organization"),
        workspace=WorkspaceContract(id="wks_default", organization_id="org_default", name="Default Workspace"),
        workspace_membership=WorkspaceMembershipContract(
            id="mem_default_owner",
            workspace_id="wks_default",
            user_id="usr_system",
            role="owner",
        ),
        workspace_quota=WorkspaceQuotaContract(
            workspace_id="wks_default",
            runs_per_day=100,
            model_tokens_per_day=1_000_000,
            storage_mb=1024,
        ),
    )
