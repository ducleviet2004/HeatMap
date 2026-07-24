from uuid import UUID

import shapely
from geoalchemy2.shape import from_shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import GPSEvent
from app.schemas.gps import GpsEventCreate


class GPSEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def exists_by_event_id(self, event_id: UUID) -> bool:
        stmt = select(GPSEvent).where(GPSEvent.event_id == event_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create(self, data: GpsEventCreate) -> GPSEvent:
        point = shapely.shape(data.raw_geometry.model_dump())
        geom = from_shape(point, srid=4326)
        event = GPSEvent(
            event_id=data.event_id,
            trip_id=data.trip_id,
            driver_id=data.driver_id,
            sequence_no=data.sequence_no,
            recorded_at=data.recorded_at,
            raw_geometry=geom,
            accuracy_m=data.accuracy_m,
            speed_kmh=data.speed_kmh,
            heading=data.heading,
            payload_metadata=data.payload_metadata,
        )
        self.session.add(event)
        await self.session.flush()
        return event
