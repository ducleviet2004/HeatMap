"""Ghi trip_route_hexes theo cách idempotent."""

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import TripRouteHex
from app.schemas.h3_grid import TripRouteHexRecord


class TripRouteHexRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert_unique(self, records: list[TripRouteHexRecord]) -> int:
        """Bỏ qua record đã tồn tại để retry worker không làm tăng count."""
        if not records:
            return 0

        statement = (
            insert(TripRouteHex)
            .values([record.model_dump() for record in records])
            .on_conflict_do_nothing(
                constraint="pk_trip_route_hexes",
            )
            .returning(TripRouteHex.hex_id)
        )
        result = await self.session.execute(statement)
        return len(result.scalars().all())
