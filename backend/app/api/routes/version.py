from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.status import VersionResponse

router = APIRouter(tags=["system"])


@router.get("/version", response_model=VersionResponse)
async def version(settings: Annotated[Settings, Depends(get_settings)]) -> VersionResponse:
    return VersionResponse(
        application=settings.app_version,
        environment=settings.app_env,
        git_sha=settings.git_sha,
        algorithm=settings.algorithm_version,
        threshold_config=settings.threshold_config_version,
        routing_data=settings.routing_data_version,
    )
