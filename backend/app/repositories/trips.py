from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Trip


class TripRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, trip: Trip) -> Trip:
        self.session.add(trip)
        await self.session.flush()
        return trip

    async def get_by_id(self, trip_id: UUID) -> Trip | None:
        stmt = select(Trip).where(Trip.id == trip_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_driver(self, driver_id: UUID) -> list[Trip]:
        stmt = select(Trip).where(Trip.driver_id == driver_id).order_by(Trip.started_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
