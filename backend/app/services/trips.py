from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Trip
from app.repositories.trips import TripRepository
from app.schemas.trips import TripCreate, TripResponse


class TripService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = TripRepository(session)

    async def create_trip(self, data: TripCreate) -> TripResponse:
        trip = Trip(
            external_id=data.external_id,
            driver_id=data.driver_id,
            status=data.status,
            started_at=data.started_at,
        )
        trip = await self.repository.create(trip)
        return TripResponse(
            id=trip.id,
            external_id=trip.external_id,
            driver_id=trip.driver_id,
            status=trip.status,
            started_at=trip.started_at,
            ended_at=trip.ended_at,
            created_at=trip.created_at,
            updated_at=trip.updated_at,
        )

    async def get_trip(self, trip_id: UUID) -> TripResponse | None:
        trip = await self.repository.get_by_id(trip_id)
        if trip is None:
            return None
        return TripResponse(
            id=trip.id,
            external_id=trip.external_id,
            driver_id=trip.driver_id,
            status=trip.status,
            started_at=trip.started_at,
            ended_at=trip.ended_at,
            created_at=trip.created_at,
            updated_at=trip.updated_at,
        )
