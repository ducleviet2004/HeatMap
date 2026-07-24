from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.schemas.gps import GeoJsonPoint, GpsEventCreate, GpsGapReason
from app.services.gps_gap import GpsGapService

START = datetime(2026, 1, 1, tzinfo=UTC)


def event(sequence_no: int, seconds: float) -> GpsEventCreate:
    return GpsEventCreate(
        event_id=uuid4(),
        trip_id=uuid4(),
        driver_id=uuid4(),
        sequence_no=sequence_no,
        recorded_at=START + timedelta(seconds=seconds),
        raw_geometry=GeoJsonPoint(coordinates=[106.7, 10.77]),
    )


def test_gap_below_15_seconds_stays_in_same_segment_without_reason() -> None:
    result = GpsGapService().analyze([event(1, 0), event(2, 14.9)])

    assert len(result.segments) == 1
    assert result.gaps == []


@pytest.mark.parametrize("duration", [15, 60, 120])
def test_gap_from_15_to_120_seconds_is_flagged_but_not_split(duration: float) -> None:
    result = GpsGapService().analyze([event(1, 0), event(2, duration)])

    assert len(result.segments) == 1
    assert result.gaps[0].reason_code == GpsGapReason.MEDIUM_GAP
    assert result.gaps[0].split_segment is False


def test_gap_over_120_seconds_splits_trace_without_fabricating_points() -> None:
    points = [event(1, 0), event(2, 10), event(3, 131), event(4, 140)]

    result = GpsGapService().analyze(points)

    assert [[point.sequence_no for point in segment] for segment in result.segments] == [
        [1, 2],
        [3, 4],
    ]
    assert result.gaps[0].reason_code == GpsGapReason.LONG_GAP_SPLIT
    assert result.gaps[0].split_segment is True
    assert sum(map(len, result.segments)) == len(points)


def test_non_increasing_timestamps_are_not_misclassified_as_gap() -> None:
    result = GpsGapService().analyze([event(1, 10), event(2, 10)])

    assert len(result.segments) == 1
    assert result.gaps == []
