from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import PlannedRoute
from app.repositories.matched_segments import MatchedSegmentRepository
from app.repositories.planned_routes import PlannedRouteRepository
from app.repositories.trips import TripRepository
from app.schemas.comparison import (
    GpsGapInfo,
    MatchedSegmentSummary,
    PlannedRouteSummary,
    RouteComparisonResponse,
)


class TripComparisonService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.trip_repo = TripRepository(session)
        self.route_repo = PlannedRouteRepository(session)
        self.matched_repo = MatchedSegmentRepository(session)

    @staticmethod
    def _ordered_edge_ids(route: PlannedRoute) -> list[str]:
        if not isinstance(route.ordered_edge_ids, list):
            return []
        return [str(e) for e in route.ordered_edge_ids]

    async def get_comparison(self, trip_id: UUID) -> RouteComparisonResponse | None:
        trip = await self.trip_repo.get_by_id(trip_id)
        if trip is None:
            return None

        planned_route_raw = await self.route_repo.get_latest_by_trip(trip_id)
        planned_route: PlannedRouteSummary | None = None
        if planned_route_raw is not None:
            geometry_geojson = self.route_repo.wkb_to_geojson(planned_route_raw.geometry)
            planned_route = PlannedRouteSummary(
                id=planned_route_raw.id,
                route_version=planned_route_raw.route_version,
                routing_data_version=planned_route_raw.routing_data_version,
                route_source=planned_route_raw.route_source,
                valid_from=planned_route_raw.valid_from,
                valid_to=planned_route_raw.valid_to,
                geometry=geometry_geojson.model_dump(),
                ordered_edge_ids=self._ordered_edge_ids(planned_route_raw),
            )

        matched_raw = await self.matched_repo.get_by_trip(trip_id)
        matched_segments: list[MatchedSegmentSummary] = []
        gps_gaps: list[GpsGapInfo] = []
        for seg in matched_raw:
            geometry_dict = self.matched_repo.wkb_to_geojson(seg.geometry)
            matched_segments.append(
                MatchedSegmentSummary(
                    id=seg.id,
                    segment_no=seg.segment_no,
                    result_state=seg.result_state,
                    confidence=seg.confidence,
                    geometry=geometry_dict,
                    ordered_edge_ids=self.matched_repo.ordered_edge_ids_to_list(
                        seg.ordered_edge_ids
                    ),
                    gap_before=seg.gap_before,
                    match_status=seg.match_status,
                    reason_code=seg.reason_code,
                    processed_at=seg.processed_at,
                )
            )
            if seg.gap_before:
                gps_gaps.append(
                    GpsGapInfo(
                        segment_no=seg.segment_no,
                        gap_before=seg.gap_before,
                        missing_length_m=None,
                    )
                )

        return RouteComparisonResponse(
            trip_id=trip.id,
            trip_status=trip.status,
            started_at=trip.started_at,
            ended_at=trip.ended_at,
            planned_route=planned_route,
            matched_segments=matched_segments,
            gps_gaps=gps_gaps,
            total_gaps=len(gps_gaps),
        )
