"""Unit tests for PostGIS database schema and SQLAlchemy ORM models."""

import uuid
from datetime import datetime, timezone

import pytest
from app.core.models import (
    Base,
    Driver,
    GPSEvent,
    H3Aggregate,
    MatchedSegment,
    PlannedRoute,
    Trip,
    TripBypassSegment,
    TripRouteHex,
)


def test_orm_models_metadata() -> None:
    """Verify all 8 tables are present in SQLAlchemy Base metadata."""
    table_names = set(Base.metadata.tables.keys())
    expected_tables = {
        "drivers",
        "trips",
        "planned_routes",
        "gps_events",
        "matched_segments",
        "trip_bypass_segments",
        "trip_route_hexes",
        "h3_aggregates",
    }
    assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}"


def test_driver_model_instantiation() -> None:
    """Verify Driver model creation."""
    driver_id = uuid.uuid4()
    driver = Driver(
        id=driver_id,
        external_id="DRV-001",
        display_name="Nguyen Van A",
        status="active",
    )
    assert driver.id == driver_id
    assert driver.external_id == "DRV-001"
    assert driver.display_name == "Nguyen Van A"
    assert driver.status == "active"


def test_trip_model_instantiation() -> None:
    """Verify Trip model creation."""
    trip_id = uuid.uuid4()
    driver_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    trip = Trip(
        id=trip_id,
        external_id="TRIP-100",
        driver_id=driver_id,
        status="in_progress",
        started_at=now,
    )
    assert trip.id == trip_id
    assert trip.driver_id == driver_id
    assert trip.status == "in_progress"


def test_trip_route_hex_model_instantiation() -> None:
    """Verify TripRouteHex model with composite primary key."""
    trip_id = uuid.uuid4()
    planned_route_id = uuid.uuid4()
    hex_obj = TripRouteHex(
        trip_id=trip_id,
        planned_route_id=planned_route_id,
        hex_id="8928308280fffff",
        h3_resolution=9,
        is_bypass=True,
        algorithm_version="v1",
    )
    assert hex_obj.hex_id == "8928308280fffff"
    assert hex_obj.h3_resolution == 9
    assert hex_obj.is_bypass is True


def test_h3_aggregate_model_instantiation() -> None:
    """Verify H3Aggregate model creation."""
    now = datetime.now(timezone.utc)
    agg = H3Aggregate(
        bucket_start=now,
        bucket_size="1h",
        hex_id="8928308280fffff",
        h3_resolution=9,
        eligible_trip_count=100,
        bypass_trip_count=25,
        unique_driver_count=80,
        bypass_unique_driver_count=20,
        average_deviation_distance_m=45.5,
        algorithm_version="v1",
    )
    assert agg.eligible_trip_count == 100
    assert agg.bypass_trip_count == 25
    assert agg.average_deviation_distance_m == 45.5
