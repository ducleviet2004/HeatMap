from uuid import UUID

from geoalchemy2 import WKBElement
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import mapping, shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import PlannedRoute
from app.schemas.routes import GeoJsonLineString


class PlannedRouteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, route: PlannedRoute) -> PlannedRoute:
        self.session.add(route)
        await self.session.flush()
        return route

    async def get_by_id(self, route_id: UUID) -> PlannedRoute | None:
        stmt = select(PlannedRoute).where(PlannedRoute.id == route_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_trip(self, trip_id: UUID) -> list[PlannedRoute]:
        stmt = (
            select(PlannedRoute)
            .where(PlannedRoute.trip_id == trip_id)
            .order_by(PlannedRoute.route_version.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_by_trip(self, trip_id: UUID) -> PlannedRoute | None:
        stmt = (
            select(PlannedRoute)
            .where(PlannedRoute.trip_id == trip_id)
            .order_by(PlannedRoute.route_version.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def geojson_to_wkb(geometry: GeoJsonLineString) -> WKBElement:
        geom = shape(geometry.model_dump())
        return from_shape(geom, srid=4326)

    @staticmethod
    def wkb_to_geojson(wkb_elem: object) -> GeoJsonLineString:
        geom = to_shape(wkb_elem)  # type: ignore[arg-type]
        coords = mapping(geom)["coordinates"]
        return GeoJsonLineString(coordinates=coords)
