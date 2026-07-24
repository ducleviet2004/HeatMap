from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.drivers import DriverResponse
from app.schemas.gps import GeoJsonPoint, GpsEventCreate, GpsEventResponse
from app.schemas.routes import GeoJsonLineString, PlannedRouteCreate, PlannedRouteResponse
from app.schemas.trips import TripCreate, TripResponse

NOW = datetime.now(UTC)
UUID1 = UUID("00000000-0000-0000-0000-000000000001")
UUID2 = UUID("00000000-0000-0000-0000-000000000002")


class TestGpsSchemas:
    def test_gps_event_create_valid(self) -> None:
        event = GpsEventCreate(
            event_id=UUID1,
            trip_id=UUID2,
            driver_id=UUID1,
            sequence_no=1,
            recorded_at=NOW,
            raw_geometry=GeoJsonPoint(coordinates=[105.85, 21.03]),
            accuracy_m=5.0,
            speed_kmh=60.0,
        )
        assert event.event_id == UUID1
        assert event.raw_geometry.coordinates == [105.85, 21.03]

    def test_gps_event_create_default_metadata(self) -> None:
        event = GpsEventCreate(
            event_id=UUID1,
            trip_id=UUID2,
            driver_id=UUID1,
            sequence_no=1,
            recorded_at=NOW,
            raw_geometry=GeoJsonPoint(coordinates=[105.85, 21.03]),
        )
        assert event.payload_metadata == {}

    def test_gps_event_create_invalid_coordinates(self) -> None:
        with pytest.raises(ValidationError):
            GeoJsonPoint(coordinates=[105.85])

    def test_gps_event_response_valid(self) -> None:
        event = GpsEventResponse(
            id=1,
            event_id=UUID1,
            trip_id=UUID2,
            driver_id=UUID1,
            sequence_no=1,
            recorded_at=NOW,
            received_at=NOW,
            raw_geometry=GeoJsonPoint(coordinates=[105.85, 21.03]),
            payload_metadata={"source": "mobile"},
        )
        assert event.id == 1
        assert event.payload_metadata["source"] == "mobile"


class TestTripSchemas:
    def test_trip_create_valid(self) -> None:
        trip = TripCreate(
            external_id="TRIP-001",
            driver_id=UUID1,
            started_at=NOW,
        )
        assert trip.external_id == "TRIP-001"
        assert trip.status == "planned"

    def test_trip_create_custom_status(self) -> None:
        trip = TripCreate(
            external_id="TRIP-002",
            driver_id=UUID1,
            status="in_progress",
            started_at=NOW,
        )
        assert trip.status == "in_progress"

    def test_trip_create_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            TripCreate(**{"external_id": "TRIP-003"})

    def test_trip_response_valid(self) -> None:
        trip = TripResponse(
            id=UUID1,
            external_id="TRIP-001",
            driver_id=UUID2,
            status="completed",
            started_at=NOW,
            created_at=NOW,
            updated_at=NOW,
        )
        assert trip.status == "completed"
        assert trip.ended_at is None


class TestRouteSchemas:
    def test_planned_route_create_valid(self) -> None:
        route = PlannedRouteCreate(
            trip_id=UUID1,
            geometry=GeoJsonLineString(
                coordinates=[[105.85, 21.03], [105.86, 21.04], [105.87, 21.05]]
            ),
            ordered_edge_ids=["10->20", "20->30"],
            valid_from=NOW,
        )
        assert route.route_version == 1
        assert len(route.geometry.coordinates) == 3
        assert route.ordered_edge_ids == ["10->20", "20->30"]

    def test_planned_route_response_valid(self) -> None:
        route = PlannedRouteResponse(
            id=UUID1,
            trip_id=UUID2,
            route_version=2,
            routing_data_version="v2",
            route_source="osrm",
            geometry=GeoJsonLineString(coordinates=[[105.85, 21.03], [105.86, 21.04]]),
            ordered_edge_ids=["10->20"],
            valid_from=NOW,
            created_at=NOW,
        )
        assert route.route_version == 2
        assert route.ordered_edge_ids == ["10->20"]

    def test_planned_route_invalid_geometry(self) -> None:
        with pytest.raises(ValidationError):
            GeoJsonLineString(coordinates=[])


class TestDriverSchemas:
    def test_driver_response_valid(self) -> None:
        driver = DriverResponse(
            id=UUID1,
            external_id="DRV-001",
            display_name="John Doe",
            status="active",
            created_at=NOW,
            updated_at=NOW,
        )
        assert driver.external_id == "DRV-001"
        assert driver.display_name == "John Doe"
