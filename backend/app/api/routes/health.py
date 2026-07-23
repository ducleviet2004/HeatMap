from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_readiness_service
from app.core.config import Settings, get_settings
from app.schemas.status import HealthResponse, ReadinessResponse
from app.services.readiness import ReadinessService

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(version=settings.app_version)


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness(
    service: Annotated[ReadinessService, Depends(get_readiness_service)],
) -> ReadinessResponse:
    return await service.check()
