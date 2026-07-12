from typing import Literal

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
