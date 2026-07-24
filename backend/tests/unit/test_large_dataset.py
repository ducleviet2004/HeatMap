"""Unit test suite for Benchmark Dataset v2 generator (seed_large_dataset.py)."""

from unittest.mock import MagicMock, patch

from app.db.seed_large_dataset import (
    generate_drivers,
    generate_gps_events_batch,
    generate_planned_routes,
    generate_trips,
    seed_large_dataset,
)


def test_generate_drivers() -> None:
    drivers = generate_drivers(count=20)
    assert len(drivers) == 20
    assert "full_name" in drivers[0]
    assert "phone_number" in drivers[0]
    assert "id" in drivers[0]


def test_generate_trips() -> None:
    drivers = generate_drivers(count=5)
    trips = generate_trips(drivers, count=15)
    assert len(trips) == 15
    assert all(t["driver_id"] in [d["id"] for d in drivers] for t in trips)


def test_generate_planned_routes() -> None:
    drivers = generate_drivers(count=2)
    trips = generate_trips(drivers, count=5)
    routes = generate_planned_routes(trips)
    assert len(routes) == 5
    assert all(len(r["coords"]) >= 4 for r in routes)


def test_generate_gps_events_batch() -> None:
    drivers = generate_drivers(count=2)
    trips = generate_trips(drivers, count=5)
    routes = generate_planned_routes(trips)
    events = generate_gps_events_batch(routes, total_events_needed=100)

    assert len(events) == 100
    sample = events[0]
    assert "latitude" in sample
    assert "longitude" in sample
    assert "accuracy_m" in sample
    assert "speed_kmh" in sample
    assert "recorded_at" in sample


@patch("app.db.seed_large_dataset.create_engine")
@patch("app.db.seed_large_dataset.sessionmaker")
def test_seed_large_dataset_mock(
    mock_sessionmaker: MagicMock, mock_create_engine: MagicMock
) -> None:
    mock_session = MagicMock()
    mock_sessionmaker.return_value.return_value.__enter__.return_value = mock_session

    result = seed_large_dataset(
        database_url="postgresql+psycopg://user:pass@localhost:5432/db",
        target_points=500,
        driver_count=5,
        trip_count=10,
        batch_size=250,
    )

    assert result["drivers"] == 5
    assert result["trips"] == 10
    assert result["gps_events"] == 500
    assert mock_session.execute.call_count >= 3
