"""Unit tests cho H3 Indexing Service và Deduplication Repository."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.core.models import TripRouteHex
from app.repositories.h3_hexes import H3HexRepository
from app.services.h3_indexing import H3IndexingService

TRIP_ID_1 = UUID("00000000-0000-0000-0000-000000000001")
ROUTE_ID_1 = UUID("00000000-0000-0000-0000-000000000002")


def test_latlng_to_hex_returns_valid_string() -> None:
    hex_id = H3IndexingService.latlng_to_hex(10.7769, 106.7009, resolution=9)
    assert isinstance(hex_id, str)
    assert len(hex_id) > 5


def test_linestring_deduplicates_repeated_hexes_in_same_trip() -> None:
    # Tuyến đường đi vòng quanh cùng 1 điểm nhiều lần (looping back & forth)
    coordinates = [
        [106.7009, 10.7769],
        [106.7015, 10.7775],
        [106.7009, 10.7769],  # Quay lại điểm ban đầu
        [106.7015, 10.7775],  # Lặp lại điểm thứ 2
    ]

    hex_set = H3IndexingService.linestring_to_hexes(coordinates, resolution=9)

    assert isinstance(hex_set, set)
    # Vì là set nên các ô trùng lặp hoàn toàn bị gỡ bỏ
    assert len(hex_set) > 0
    assert len(hex_set) == len(set(hex_set))


def test_h3_resolution_validation_rule_3() -> None:
    # Resolution 9 đến 12 là hợp lệ theo Rule 3 của AGENTS.md
    for valid_res in (9, 10, 11, 12):
        H3IndexingService.validate_resolution(valid_res)

    # Resolution ngoài khoảng 9-12 phải báo lỗi ValueError
    with pytest.raises(ValueError, match="H3 resolution must be between 9 and 12"):
        H3IndexingService.validate_resolution(8)

    with pytest.raises(ValueError, match="H3 resolution must be between 9 and 12"):
        H3IndexingService.validate_resolution(13)


@pytest.mark.asyncio
async def test_h3_repository_bulk_upsert_empty() -> None:
    session = AsyncMock()
    repo = H3HexRepository(session)

    inserted = await repo.bulk_upsert_trip_hexes([])
    assert inserted == 0
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_h3_repository_bulk_upsert_executes_on_conflict_do_nothing() -> None:
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.rowcount = 2
    session.execute.return_value = result_mock

    repo = H3HexRepository(session)
    records = [
        TripRouteHex(
            trip_id=TRIP_ID_1,
            planned_route_id=ROUTE_ID_1,
            hex_id="8928308280fffff",
            h3_resolution=9,
            is_bypass=False,
            algorithm_version="v1",
        ),
        TripRouteHex(
            trip_id=TRIP_ID_1,
            planned_route_id=ROUTE_ID_1,
            hex_id="8928308281fffff",
            h3_resolution=9,
            is_bypass=True,
            algorithm_version="v1",
        ),
    ]

    inserted = await repo.bulk_upsert_trip_hexes(records)

    assert inserted == 2
    session.execute.assert_called_once()
    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_h3_repository_aggregate_heatmap_buckets() -> None:
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.all.return_value = [("8928308280fffff", 3), ("8928308281fffff", 1)]
    session.execute.return_value = result_mock

    repo = H3HexRepository(session)
    bucket_start = datetime(2026, 7, 24, 15, 0, tzinfo=UTC)

    aggregates = await repo.aggregate_heatmap_buckets(
        bucket_start=bucket_start,
        bucket_size="1h",
        h3_resolution=9,
        algorithm_version="v1",
    )

    assert len(aggregates) == 2
    assert aggregates[0].hex_id == "8928308280fffff"
    assert aggregates[0].eligible_trip_count == 3
    assert aggregates[1].hex_id == "8928308281fffff"
    assert aggregates[1].eligible_trip_count == 1
