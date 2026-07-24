from typing import cast
from uuid import UUID

from geoalchemy2 import WKBElement
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping as shape_mapping
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import MatchedSegment


class MatchedSegmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_trip(self, trip_id: UUID) -> list[MatchedSegment]:
        stmt = (
            select(MatchedSegment)
            .where(MatchedSegment.trip_id == trip_id)
            .order_by(MatchedSegment.segment_no)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def wkb_to_geojson(wkb_elem: object) -> dict[str, object]:
        geom = to_shape(cast(WKBElement, wkb_elem))
        return dict(shape_mapping(geom))

    @staticmethod
    def ordered_edge_ids_to_list(edge_ids: object) -> list[str]:
        if not isinstance(edge_ids, list):
            return []
        return [str(e) for e in edge_ids]
