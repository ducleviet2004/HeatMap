from typing import Literal

from pydantic import BaseModel

DependencyState = Literal["ok", "degraded", "unavailable", "not_configured"]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "route-deviation-api"
    version: str


class DependencyStatus(BaseModel):
    status: DependencyState
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: Literal["healthy", "degraded", "unavailable"]
    dependencies: dict[str, DependencyStatus]


class VersionResponse(BaseModel):
    application: str
    environment: str
    git_sha: str
    algorithm: str
    threshold_config: str
    routing_data: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    correlation_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
