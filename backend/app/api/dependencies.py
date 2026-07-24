from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.planned_routes import PlannedRouteService
from app.services.readiness import ReadinessService
from app.services.trips import TripService


def get_readiness_service(request: Request) -> ReadinessService:
    return request.app.state.readiness_service  # type: ignore[no-any-return]


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.database.session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_trip_service(session: SessionDep) -> TripService:
    return TripService(session)


async def get_planned_route_service(session: SessionDep) -> PlannedRouteService:
    return PlannedRouteService(session)
