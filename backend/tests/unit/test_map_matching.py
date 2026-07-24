from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest

from app.schemas.gps import GeoJsonPoint, GpsEventCreate
from app.schemas.map_matching import MapMatchStatus
from app.services.map_matching import MapMatchingService

EVENT_ID = UUID("00000000-0000-0000-0000-000000000001")
TRIP_ID = UUID("00000000-0000-0000-0000-000000000002")
DRIVER_ID = UUID("00000000-0000-0000-0000-000000000003")
STARTED_AT = datetime(2026, 7, 24, tzinfo=UTC)


class StubOsrmClient:
    def __init__(self, response: dict[str, Any] | None) -> None:
        self.response = response
        self.coordinates: list[tuple[float, float]] | None = None
        self.timestamps: list[int] | None = None
        self.radiuses: list[float] | None = None

    async def match_trace(
        self,
        coordinates: list[tuple[float, float]],
        timestamps: list[int] | None = None,
        radiuses: list[float] | None = None,
        overview: str = "full",
        geometries: str = "geojson",
    ) -> dict[str, Any] | None:
        self.coordinates = coordinates
        self.timestamps = timestamps
        self.radiuses = radiuses
        assert overview == "full"
        assert geometries == "geojson"
        return self.response


def make_event(
    sequence_no: int,
    *,
    recorded_at: datetime,
    accuracy_m: float | None = 5.0,
) -> GpsEventCreate:
    return GpsEventCreate(
        event_id=EVENT_ID,
        trip_id=TRIP_ID,
        driver_id=DRIVER_ID,
        sequence_no=sequence_no,
        recorded_at=recorded_at,
        raw_geometry=GeoJsonPoint(
            coordinates=[106.7009 - sequence_no * 0.001, 10.7769 - sequence_no * 0.001]
        ),
        accuracy_m=accuracy_m,
        speed_kmh=40.0,
    )


def successful_response() -> dict[str, Any]:
    return {
        "code": "Ok",
        "matchings": [
            {
                "confidence": 0.91,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[106.7, 10.77], [106.69, 10.76]],
                },
                "legs": [
                    {"annotation": {"nodes": [10, 20, 30]}},
                    {"annotation": {"nodes": [20, 30, 40]}},
                ],
            }
        ],
        "tracepoints": [{"location": [106.7, 10.77]}, None, {"location": [106.69, 10.76]}],
    }


@pytest.mark.asyncio
async def test_recovers_ordered_road_edges_and_confidence() -> None:
    client = StubOsrmClient(successful_response())
    service = MapMatchingService(
        client,
        routing_data_version="vietnam-2026-07-23",
        algorithm_version="osrm-match-v1",
    )
    events = [
        make_event(0, recorded_at=STARTED_AT),
        make_event(1, recorded_at=STARTED_AT + timedelta(seconds=10)),
        make_event(2, recorded_at=STARTED_AT + timedelta(seconds=20)),
    ]
    original_events = [event.model_dump(mode="json") for event in events]

    result = await service.match(events)

    assert result.status == MapMatchStatus.MATCHED
    assert result.match_confidence == 0.91
    assert result.segments[0].match_confidence == 0.91
    assert [edge.edge_id for edge in result.segments[0].ordered_road_edges] == [
        "10->20",
        "20->30",
        "30->40",
    ]
    assert result.unmatched_point_indices == [1]
    assert result.routing_data_version == "vietnam-2026-07-23"
    assert [event.model_dump(mode="json") for event in events] == original_events


@pytest.mark.asyncio
async def test_sends_coordinates_timestamps_and_accuracy_radiuses() -> None:
    client = StubOsrmClient(successful_response())
    service = MapMatchingService(
        client,
        routing_data_version="routing-v1",
        algorithm_version="algorithm-v1",
    )
    events = [
        make_event(0, recorded_at=STARTED_AT, accuracy_m=4.0),
        make_event(1, recorded_at=STARTED_AT + timedelta(seconds=5), accuracy_m=6.0),
    ]

    await service.match(events)

    assert client.coordinates == [(106.7009, 10.7769), (106.6999, 10.7759)]
    assert client.timestamps == [
        int(STARTED_AT.timestamp()),
        int((STARTED_AT + timedelta(seconds=5)).timestamp()),
    ]
    assert client.radiuses == [4.0, 6.0]


@pytest.mark.asyncio
async def test_omits_incomplete_radiuses_and_non_increasing_timestamps() -> None:
    client = StubOsrmClient(successful_response())
    service = MapMatchingService(
        client,
        routing_data_version="routing-v1",
        algorithm_version="algorithm-v1",
    )
    events = [
        make_event(0, recorded_at=STARTED_AT, accuracy_m=4.0),
        make_event(1, recorded_at=STARTED_AT, accuracy_m=None),
    ]

    await service.match(events)

    assert client.timestamps is None
    assert client.radiuses is None


@pytest.mark.asyncio
async def test_preserves_split_subtraces_and_uses_lowest_confidence() -> None:
    response = successful_response()
    response["matchings"].append(
        {
            "confidence": 0.42,
            "geometry": {
                "type": "LineString",
                "coordinates": [[106.68, 10.75], [106.67, 10.74]],
            },
            "legs": [{"annotation": {"nodes": [50, 60]}}],
        }
    )
    service = MapMatchingService(
        StubOsrmClient(response),
        routing_data_version="routing-v1",
        algorithm_version="algorithm-v1",
    )

    result = await service.match(
        [
            make_event(0, recorded_at=STARTED_AT),
            make_event(1, recorded_at=STARTED_AT + timedelta(seconds=10)),
        ]
    )

    assert len(result.segments) == 2
    assert result.segments[0].segment_no == 0
    assert result.segments[1].segment_no == 1
    assert result.match_confidence == 0.42


@pytest.mark.asyncio
async def test_long_gps_gap_is_matched_as_separate_segments() -> None:
    service = MapMatchingService(
        StubOsrmClient(successful_response()),
        routing_data_version="routing-v1",
        algorithm_version="algorithm-v1",
    )

    result = await service.match(
        [
            make_event(0, recorded_at=STARTED_AT),
            make_event(1, recorded_at=STARTED_AT + timedelta(seconds=10)),
            make_event(2, recorded_at=STARTED_AT + timedelta(seconds=131)),
            make_event(3, recorded_at=STARTED_AT + timedelta(seconds=140)),
        ]
    )

    assert len(result.segments) == 2
    assert result.segments[0].gap_before is False
    assert result.segments[1].gap_before is True
    assert result.segments[1].reason_code == "gps_gap_long_split"
    assert result.gps_gaps[0].reason_code == "gps_gap_long_split"


@pytest.mark.asyncio
async def test_reports_no_match_without_fabricating_edges() -> None:
    service = MapMatchingService(
        StubOsrmClient({"code": "NoMatch", "message": "Could not match the trace."}),
        routing_data_version="routing-v1",
        algorithm_version="algorithm-v1",
    )

    result = await service.match(
        [
            make_event(0, recorded_at=STARTED_AT),
            make_event(1, recorded_at=STARTED_AT + timedelta(seconds=10)),
        ]
    )

    assert result.status == MapMatchStatus.NO_MATCH
    assert result.match_confidence is None
    assert result.segments == []
    assert result.reason_code == "NoMatch"


@pytest.mark.asyncio
async def test_requires_at_least_two_trace_points() -> None:
    client = StubOsrmClient(successful_response())
    service = MapMatchingService(
        client,
        routing_data_version="routing-v1",
        algorithm_version="algorithm-v1",
    )

    result = await service.match([make_event(0, recorded_at=STARTED_AT)])

    assert result.status == MapMatchStatus.NO_MATCH
    assert result.reason_code == "insufficient_trace_points"
    assert client.coordinates is None


class FallbackMockOsrmClient:
    def __init__(self, succeed_at_radius: float) -> None:
        self.succeed_at_radius = succeed_at_radius
        self.attempted_radiuses: list[list[float] | None] = []

    async def match_trace(
        self,
        coordinates: list[tuple[float, float]],
        timestamps: list[int] | None = None,
        radiuses: list[float] | None = None,
        overview: str = "full",
        geometries: str = "geojson",
    ) -> dict[str, Any] | None:
        self.attempted_radiuses.append(radiuses)
        if radiuses and radiuses[0] == self.succeed_at_radius:
            return successful_response()
        return {"code": "NoMatch", "message": "Could not match trace at this radius."}


@pytest.mark.asyncio
async def test_corridor_fallback_check_recovers_on_100m_radius() -> None:
    # Fails on 5.0m (accuracy) and 50.0m, succeeds on 100.0m
    client = FallbackMockOsrmClient(succeed_at_radius=100.0)
    service = MapMatchingService(
        client,
        routing_data_version="routing-v1",
        algorithm_version="algorithm-v1",
    )

    events = [
        make_event(0, recorded_at=STARTED_AT, accuracy_m=5.0),
        make_event(1, recorded_at=STARTED_AT + timedelta(seconds=10), accuracy_m=5.0),
    ]

    result = await service.match(events)

    assert result.status == MapMatchStatus.MATCHED
    assert result.fallback_radius_m == 100.0
    # Attempted radiuses: [5.0, 5.0] -> [50.0, 50.0] -> [100.0, 100.0]
    assert len(client.attempted_radiuses) == 3
    assert client.attempted_radiuses[2] == [100.0, 100.0]


@pytest.mark.asyncio
async def test_corridor_fallback_fails_after_all_levels_exhausted() -> None:
    # Fails on all radiuses (succeed_at_radius impossible 999.0m)
    client = FallbackMockOsrmClient(succeed_at_radius=999.0)
    service = MapMatchingService(
        client,
        routing_data_version="routing-v1",
        algorithm_version="algorithm-v1",
    )

    events = [
        make_event(0, recorded_at=STARTED_AT, accuracy_m=5.0),
        make_event(1, recorded_at=STARTED_AT + timedelta(seconds=10), accuracy_m=5.0),
    ]

    result = await service.match(events)

    assert result.status == MapMatchStatus.NO_MATCH
    assert result.reason_code == "NoMatch"
    # Total attempts: base (5.0m) + 50m + 100m + 200m = 4 attempts
    assert len(client.attempted_radiuses) == 4
