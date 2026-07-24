from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi import status as http_status

from app.api.dependencies import get_planned_route_service
from app.schemas.routes import PlannedRouteCreate, PlannedRouteResponse
from app.services.planned_routes import PlannedRouteService

router = APIRouter(tags=["planned-routes"])


@router.post(
    "/planned-routes", response_model=PlannedRouteResponse, status_code=http_status.HTTP_201_CREATED
)
async def create_planned_route(
    data: PlannedRouteCreate,
    service: Annotated[PlannedRouteService, Depends(get_planned_route_service)],
) -> PlannedRouteResponse:
    return await service.create_route(data)


@router.get("/trips/{trip_id}/planned-routes", response_model=list[PlannedRouteResponse])
async def list_planned_routes(
    trip_id: UUID,
    service: Annotated[PlannedRouteService, Depends(get_planned_route_service)],
) -> list[PlannedRouteResponse]:
    return await service.get_routes_by_trip(trip_id)
