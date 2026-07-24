from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.comparison import (
    GpsGapInfo,
    MatchedSegmentSummary,
    PlannedRouteSummary,
    RouteComparisonResponse,
)
from app.schemas.heatmap import (
    HeatmapFeaturePropertiesWithMetrics,
    HeatmapFeatureWithMetrics,
    HeatmapFilteredResponse,
    HeatmapQueryParams,
)

NOW = datetime.now(UTC)
UUID1 = UUID("00000000-0000-0000-0000-000000000001")
UUID2 = UUID("00000000-0000-0000-0000-000000000002")


class TestHeatmapQueryParams:
    def test_defaults(self) -> None:
        params = HeatmapQueryParams()
        assert params.start_time is None
        assert params.end_time is None
        assert params.driver_id is None
        assert params.h3_resolution == 9

    def test_with_filters(self) -> None:
        params = HeatmapQueryParams(
            start_time=NOW,
            end_time=NOW,
            driver_id=UUID1,
            h3_resolution=10,
        )
        assert params.start_time == NOW
        assert params.end_time == NOW
        assert params.driver_id == UUID1
        assert params.h3_resolution == 10

    def test_h3_resolution_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            HeatmapQueryParams(h3_resolution=8)
        with pytest.raises(ValidationError):
            HeatmapQueryParams(h3_resolution=13)


class TestHeatmapFeatureWithMetrics:
    def test_default_properties(self) -> None:
        feat = HeatmapFeatureWithMetrics()
        assert feat.properties.heat_weight == 0.0
        assert feat.properties.display_weight == 0.0
        assert feat.properties.bypass_trip_count == 0
        assert feat.properties.eligible_trip_count == 0
        assert feat.properties.unique_driver_count == 0
        assert feat.properties.average_deviation_distance_m == 0.0

    def test_with_metrics(self) -> None:
        props = HeatmapFeaturePropertiesWithMetrics(
            heat_weight=10.0,
            display_weight=5.0,
            bypass_trip_count=3,
            eligible_trip_count=10,
            unique_driver_count=7,
            average_deviation_distance_m=25.5,
        )
        feat = HeatmapFeatureWithMetrics(properties=props)
        assert feat.properties.heat_weight == 10.0
        assert feat.properties.bypass_trip_count == 3


class TestHeatmapFilteredResponse:
    def test_empty_response(self) -> None:
        resp = HeatmapFilteredResponse()
        assert resp.type == "FeatureCollection"
        assert resp.features == []
        assert resp.query_params is None
        assert resp.total_bypass_trips == 0
        assert resp.total_eligible_trips == 0

    def test_with_features_and_params(self) -> None:
        params = HeatmapQueryParams(h3_resolution=10)
        props = HeatmapFeaturePropertiesWithMetrics(eligible_trip_count=5)
        feat = HeatmapFeatureWithMetrics(properties=props)
        resp = HeatmapFilteredResponse(
            features=[feat],
            query_params=params,
            total_bypass_trips=2,
            total_eligible_trips=5,
        )
        assert len(resp.features) == 1
        assert resp.query_params.h3_resolution == 10
        assert resp.total_eligible_trips == 5


class TestRouteComparisonSchemas:
    def test_gps_gap_info(self) -> None:
        gap = GpsGapInfo(segment_no=2, gap_before=True, missing_length_m=15.5)
        assert gap.segment_no == 2
        assert gap.gap_before is True
        assert gap.missing_length_m == 15.5

    def test_gps_gap_info_defaults(self) -> None:
        gap = GpsGapInfo(segment_no=1, gap_before=True)
        assert gap.missing_length_m is None

    def test_matched_segment_summary(self) -> None:
        seg = MatchedSegmentSummary(
            id=UUID1,
            segment_no=1,
            result_state="matched",
            confidence=0.95,
            geometry={"type": "LineString", "coordinates": [[106.7, 10.7], [106.8, 10.8]]},
            ordered_edge_ids=["edge1", "edge2"],
            gap_before=False,
            match_status="success",
            processed_at=NOW,
        )
        assert seg.id == UUID1
        assert seg.confidence == 0.95
        assert seg.ordered_edge_ids == ["edge1", "edge2"]

    def test_planned_route_summary(self) -> None:
        route = PlannedRouteSummary(
            id=UUID1,
            route_version=1,
            routing_data_version="v1.0",
            route_source="osrm",
            valid_from=NOW,
            geometry={"type": "LineString", "coordinates": [[106.7, 10.7]]},
            ordered_edge_ids=["e1"],
        )
        assert route.route_version == 1
        assert route.geometry["type"] == "LineString"

    def test_route_comparison_response(self) -> None:
        resp = RouteComparisonResponse(
            trip_id=UUID1,
            trip_status="final",
            started_at=NOW,
            ended_at=NOW,
            planned_route=None,
            matched_segments=[],
            gps_gaps=[],
            total_gaps=0,
        )
        assert resp.trip_id == UUID1
        assert resp.total_gaps == 0
        assert resp.planned_route is None

    def test_route_comparison_with_gaps(self) -> None:
        gap1 = GpsGapInfo(segment_no=2, gap_before=True, missing_length_m=10.0)
        gap2 = GpsGapInfo(segment_no=5, gap_before=True, missing_length_m=None)
        resp = RouteComparisonResponse(
            trip_id=UUID1,
            trip_status="final",
            started_at=NOW,
            planned_route=None,
            matched_segments=[],
            gps_gaps=[gap1, gap2],
            total_gaps=2,
        )
        assert resp.total_gaps == 2
        assert resp.gps_gaps[0].segment_no == 2
        assert resp.gps_gaps[1].missing_length_m is None
