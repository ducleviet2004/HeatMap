from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import PlannedRoute
from app.repositories.planned_routes import PlannedRouteRepository
from app.schemas.routes import PlannedRouteCreate, PlannedRouteResponse


class PlannedRouteService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = PlannedRouteRepository(session)

    async def create_route(self, data: PlannedRouteCreate) -> PlannedRouteResponse:
        geometry_wkb = self.repository.geojson_to_wkb(data.geometry)
        route = PlannedRoute(
            trip_id=data.trip_id,
            route_version=data.route_version,
            routing_data_version=data.routing_data_version,
            route_source=data.route_source,
            geometry=geometry_wkb,
            ordered_edge_ids=data.ordered_edge_ids,
            valid_from=data.valid_from,
        )
        route = await self.repository.create(route)
        geometry_geojson = self.repository.wkb_to_geojson(route.geometry)
        return PlannedRouteResponse(
            id=route.id,
            trip_id=route.trip_id,
            route_version=route.route_version,
            routing_data_version=route.routing_data_version,
            route_source=route.route_source,
            geometry=geometry_geojson,
            ordered_edge_ids=self._ordered_edge_ids(route),
            valid_from=route.valid_from,
            valid_to=route.valid_to,
            created_at=route.created_at,
        )

    async def get_routes_by_trip(self, trip_id: UUID) -> list[PlannedRouteResponse]:
        routes = await self.repository.list_by_trip(trip_id)
        return [
            PlannedRouteResponse(
                id=r.id,
                trip_id=r.trip_id,
                route_version=r.route_version,
                routing_data_version=r.routing_data_version,
                route_source=r.route_source,
                geometry=self.repository.wkb_to_geojson(r.geometry),
                ordered_edge_ids=self._ordered_edge_ids(r),
                valid_from=r.valid_from,
                valid_to=r.valid_to,
                created_at=r.created_at,
            )
            for r in routes
        ]

    @staticmethod
    def _ordered_edge_ids(route: PlannedRoute) -> list[str]:
        """Chuẩn hóa JSONB thành danh sách string cho API và thuật toán so sánh."""
        if not isinstance(route.ordered_edge_ids, list):
            return []
        return [str(edge_id) for edge_id in route.ordered_edge_ids]
