"""Unit tests for Demo Seed Dataset generator and seeder."""

from scripts.generate_seed_dataset import generate_dataset


def test_seed_dataset_generation_count_and_determinism() -> None:
    """Verify generated seed dataset count and 100% determinism."""
    dataset1 = generate_dataset()

    assert len(dataset1["drivers"]) == 10
    assert len(dataset1["trips"]) == 50
    assert len(dataset1["planned_routes"]) == 50
    assert len(dataset1["gps_events"]) >= 50000

    # Determinism test
    dataset2 = generate_dataset()
    assert dataset1["drivers"] == dataset2["drivers"]
    assert dataset1["trips"] == dataset2["trips"]
    assert len(dataset1["gps_events"]) == len(dataset2["gps_events"])

    # Check first GPS event structure
    first_event = dataset1["gps_events"][0]
    assert "latitude" in first_event
    assert "longitude" in first_event
    assert "accuracy_m" in first_event
    assert first_event["raw_geometry"]["type"] == "Point"
