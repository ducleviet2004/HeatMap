import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.redis_streams import RedisStreams
from app.repositories.gps_events import GPSEventRepository
from app.schemas.gps import GpsEventCreate

logger = logging.getLogger(__name__)


class GpsIngestionService:
    def __init__(self, session: AsyncSession, redis: RedisStreams) -> None:
        self.repository = GPSEventRepository(session)
        self.redis = redis

    async def ingest(self, data: GpsEventCreate, correlation_id: str = "") -> bool:
        existing = await self.repository.exists_by_event_id(data.event_id)
        if existing:
            logger.info("Duplicate event %s, accepting silently", data.event_id)
            return True

        await self.repository.create(data)

        longitude, latitude = data.raw_geometry.coordinates
        await self.redis.publish_gps_event(
            event_id=data.event_id,
            trip_id=data.trip_id,
            driver_id=data.driver_id,
            sequence_no=data.sequence_no,
            recorded_at=data.recorded_at,
            longitude=longitude,
            latitude=latitude,
            accuracy_m=data.accuracy_m,
            speed_kmh=data.speed_kmh,
            heading=data.heading,
            correlation_id=correlation_id,
        )

        logger.info("Ingested GPS event %s for trip %s", data.event_id, data.trip_id)
        return True
