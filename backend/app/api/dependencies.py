from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.redis_streams import RedisStreams
from app.services.gps_ingestion import GpsIngestionService
from app.services.planned_routes import PlannedRouteService
from app.services.readiness import ReadinessService
from app.services.trip_comparison import TripComparisonService
from app.services.trips import TripService


def get_readiness_service(request: Request) -> ReadinessService:
    return cast(ReadinessService, request.app.state.readiness_service)


def get_redis_streams(request: Request) -> RedisStreams:
    return cast(RedisStreams, request.app.state.redis)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.database.session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_trip_service(session: SessionDep) -> TripService:
    return TripService(session)


async def get_planned_route_service(session: SessionDep) -> PlannedRouteService:
    return PlannedRouteService(session)


async def get_gps_ingestion_service(
    session: SessionDep,
    redis: Annotated[RedisStreams, Depends(get_redis_streams)],
) -> GpsIngestionService:
    return GpsIngestionService(session, redis)


async def get_trip_comparison_service(session: SessionDep) -> TripComparisonService:
    return TripComparisonService(session)
