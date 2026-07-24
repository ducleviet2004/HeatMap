from uuid import uuid4

import h3
import pytest

from app.schemas.h3_grid import BypassGeometry
from app.services.h3_grid import BypassH3Service


def test_converts_bypass_to_all_supported_resolutions() -> None:
    service = BypassH3Service()
    segment = BypassGeometry(coordinates=[(106.70098, 10.77689), (106.70220, 10.77740)])

    result = service.convert(
        trip_id=uuid4(),
        planned_route_id=uuid4(),
        bypass_segments=[segment],
    )

    assert {record.h3_resolution for record in result.records} == {9, 10, 11, 12}
    assert all(h3.is_valid_cell(record.hex_id) for record in result.records)
    assert all(record.is_bypass for record in result.records)


def test_same_trip_hex_is_emitted_once_when_segments_overlap() -> None:
    service = BypassH3Service(resolutions=(9,))
    segment = BypassGeometry(coordinates=[(106.70098, 10.77689), (106.70105, 10.77695)])

    result = service.convert(
        trip_id=uuid4(),
        planned_route_id=uuid4(),
        bypass_segments=[segment, segment],
    )

    keys = {(record.trip_id, record.hex_id, record.h3_resolution) for record in result.records}
    assert len(result.records) == len(keys)
    assert result.unique_hex_count == len(keys)


def test_unconfirmed_segment_does_not_create_bypass_hex() -> None:
    service = BypassH3Service(resolutions=(9,))

    result = service.convert(
        trip_id=uuid4(),
        planned_route_id=uuid4(),
        bypass_segments=[
            BypassGeometry(
                coordinates=[(106.70098, 10.77689), (106.70220, 10.77740)],
                confirmed=False,
            )
        ],
    )

    assert result.records == []


@pytest.mark.parametrize("resolutions", [(), (8,), (13,), (9, 12, 13)])
def test_rejects_resolution_outside_9_to_12(resolutions: tuple[int, ...]) -> None:
    with pytest.raises(ValueError, match="between 9 and 12"):
        BypassH3Service(resolutions=resolutions)


def test_removes_duplicate_resolution_configuration() -> None:
    service = BypassH3Service(resolutions=(12, 9, 9))

    assert service.resolutions == (9, 12)
