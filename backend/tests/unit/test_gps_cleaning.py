from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.core.config import Settings
from app.schemas.gps import GeoJsonPoint, GpsEventCreate, GpsRejectionReason
from app.services.gps_cleaning import GpsCleaningService

EVENT_ID = UUID("00000000-0000-0000-0000-000000000001")
TRIP_ID = UUID("00000000-0000-0000-0000-000000000002")
DRIVER_ID = UUID("00000000-0000-0000-0000-000000000003")
RECORDED_AT = datetime(2026, 7, 24, tzinfo=UTC)


def make_event(*, accuracy_m: float | None, speed_kmh: float | None) -> GpsEventCreate:
    return GpsEventCreate(
        event_id=EVENT_ID,
        trip_id=TRIP_ID,
        driver_id=DRIVER_ID,
        sequence_no=1,
        recorded_at=RECORDED_AT,
        raw_geometry=GeoJsonPoint(coordinates=[106.7009, 10.7769]),
        accuracy_m=accuracy_m,
        speed_kmh=speed_kmh,
        payload_metadata={"source": "test"},
    )


@pytest.fixture
def service() -> GpsCleaningService:
    return GpsCleaningService(
        max_accuracy_m=30.0,
        max_speed_kmh=120.0,
        threshold_config_version="v1",
    )


def test_accepts_normal_event(service: GpsCleaningService) -> None:
    result = service.evaluate(make_event(accuracy_m=5.0, speed_kmh=40.0))

    assert result.accepted is True
    assert result.reasons == ()
    assert result.threshold_config_version == "v1"


@pytest.mark.parametrize(
    ("accuracy_m", "accepted"),
    [(30.0, True), (30.1, False)],
)
def test_accuracy_threshold_is_strictly_greater_than(
    service: GpsCleaningService, accuracy_m: float, accepted: bool
) -> None:
    result = service.evaluate(make_event(accuracy_m=accuracy_m, speed_kmh=40.0))

    assert result.accepted is accepted
    assert (GpsRejectionReason.POOR_ACCURACY in result.reasons) is not accepted


@pytest.mark.parametrize(
    ("speed_kmh", "accepted"),
    [(120.0, True), (120.1, False)],
)
def test_speed_threshold_is_strictly_greater_than(
    service: GpsCleaningService, speed_kmh: float, accepted: bool
) -> None:
    result = service.evaluate(make_event(accuracy_m=5.0, speed_kmh=speed_kmh))

    assert result.accepted is accepted
    assert (GpsRejectionReason.EXCESSIVE_SPEED in result.reasons) is not accepted


def test_reports_all_rejection_reasons(service: GpsCleaningService) -> None:
    result = service.evaluate(make_event(accuracy_m=31.0, speed_kmh=121.0))

    assert result.accepted is False
    assert result.reasons == (
        GpsRejectionReason.POOR_ACCURACY,
        GpsRejectionReason.EXCESSIVE_SPEED,
    )


def test_missing_measurements_are_not_rejected(service: GpsCleaningService) -> None:
    result = service.evaluate(make_event(accuracy_m=None, speed_kmh=None))

    assert result.accepted is True
    assert result.reasons == ()


def test_thresholds_are_loaded_from_settings() -> None:
    settings = Settings(
        gps_max_accuracy_m=50.0,
        gps_max_speed_kmh=150.0,
        threshold_config_version="lenient-v2",
    )
    service = GpsCleaningService.from_settings(settings)

    result = service.evaluate(make_event(accuracy_m=40.0, speed_kmh=140.0))

    assert result.accepted is True
    assert result.threshold_config_version == "lenient-v2"


def test_filter_does_not_modify_raw_gps(service: GpsCleaningService) -> None:
    accepted = make_event(accuracy_m=10.0, speed_kmh=50.0)
    rejected = make_event(accuracy_m=40.0, speed_kmh=130.0)
    original_accepted = accepted.model_dump(mode="json")
    original_rejected = rejected.model_dump(mode="json")

    cleaned = service.filter_events([accepted, rejected])

    assert cleaned == [accepted]
    assert cleaned[0] is accepted
    assert accepted.model_dump(mode="json") == original_accepted
    assert rejected.model_dump(mode="json") == original_rejected
