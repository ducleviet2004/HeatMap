from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import SessionDep
from app.schemas.heatmap import HeatmapFilteredResponse, HeatmapQueryParams
from app.services.heatmap import HeatmapService

router = APIRouter(tags=["heatmap"])


@router.get("/heatmap", response_model=HeatmapFilteredResponse)
async def get_heatmap(
    session: SessionDep,
    start_time: Annotated[
        datetime | None,
        Query(description="Filter trips starting after this time"),
    ] = None,
    end_time: Annotated[
        datetime | None,
        Query(description="Filter trips starting before this time"),
    ] = None,
    driver_id: Annotated[UUID | None, Query(description="Filter by driver ID")] = None,
    h3_resolution: Annotated[
        int,
        Query(ge=9, le=12, description="H3 resolution (9-12)"),
    ] = 9,
) -> HeatmapFilteredResponse:
    params = HeatmapQueryParams(
        start_time=start_time,
        end_time=end_time,
        driver_id=driver_id,
        h3_resolution=h3_resolution,
    )
    service = HeatmapService(session)
    return await service.query_filtered(params)
