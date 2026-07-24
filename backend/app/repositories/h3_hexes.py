"""Repository xử lý lưu trữ và aggregate H3 Spatial Grid tuân thủ Deduplication Rule."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import H3Aggregate, TripRouteHex


class H3HexRepository:
    """Quản lý các thao tác DB bất đồng bộ cho bảng trip_route_hexes và h3_aggregates."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_upsert_trip_hexes(self, hex_records: list[TripRouteHex]) -> int:
        """Thực hiện bulk insert idempotent vào trip_route_hexes với ON CONFLICT DO NOTHING.

        Đảm bảo Deduplication ở tầng Storage: Một cặp (trip_id, hex_id) tại một resolution
        và algorithm_version chỉ tồn tại 1 bản ghi duy nhất trong CSDL.
        """
        if not hex_records:
            return 0

        values = [
            {
                "trip_id": record.trip_id,
                "planned_route_id": record.planned_route_id,
                "hex_id": record.hex_id,
                "h3_resolution": record.h3_resolution,
                "is_bypass": record.is_bypass,
                "algorithm_version": record.algorithm_version,
            }
            for record in hex_records
        ]

        stmt = pg_insert(TripRouteHex).values(values)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=[
                "trip_id",
                "planned_route_id",
                "hex_id",
                "h3_resolution",
                "algorithm_version",
            ]
        )

        result = await self.session.execute(stmt)
        await self.session.flush()
        return int(result.rowcount or 0)

    async def get_hexes_by_trip(self, trip_id: UUID, resolution: int = 9) -> list[TripRouteHex]:
        """Truy vấn tất cả các ô H3 hexes của 1 trip_id theo độ phân giải."""
        stmt = select(TripRouteHex).where(
            TripRouteHex.trip_id == trip_id,
            TripRouteHex.h3_resolution == resolution,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def aggregate_heatmap_buckets(
        self,
        bucket_start: datetime,
        bucket_size: str = "1h",
        h3_resolution: int = 9,
        algorithm_version: str = "v1",
    ) -> list[H3Aggregate]:
        """Tổng hợp heat_weight cho từng ô H3 theo bucket thời gian.

        Đảm bảo 1 trip_id chỉ tính heat_weight 1 lần trên 1 hex_id thông qua
        COUNT(DISTINCT trip_id).
        """
        stmt = (
            select(
                TripRouteHex.hex_id,
                func.count(func.distinct(TripRouteHex.trip_id)).label("eligible_trip_count"),
            )
            .where(
                TripRouteHex.h3_resolution == h3_resolution,
                TripRouteHex.algorithm_version == algorithm_version,
            )
            .group_by(TripRouteHex.hex_id)
        )

        result = await self.session.execute(stmt)
        aggregates: list[H3Aggregate] = []

        for row in result.all():
            hex_id_val, count_val = row[0], row[1]
            aggregates.append(
                H3Aggregate(
                    bucket_start=bucket_start,
                    bucket_size=bucket_size,
                    hex_id=hex_id_val,
                    h3_resolution=h3_resolution,
                    algorithm_version=algorithm_version,
                    eligible_trip_count=count_val,
                )
            )

        return aggregates

    async def get_heatmap_features(
        self,
        h3_resolution: int = 9,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        algorithm_version: str = "v1",
    ) -> list[H3Aggregate]:
        """Query h3_aggregates with optional time range and resolution filters."""
        stmt = select(H3Aggregate).where(
            H3Aggregate.h3_resolution == h3_resolution,
            H3Aggregate.algorithm_version == algorithm_version,
        )
        if start_time is not None:
            stmt = stmt.where(H3Aggregate.bucket_start >= start_time)
        if end_time is not None:
            stmt = stmt.where(H3Aggregate.bucket_start <= end_time)
        stmt = stmt.order_by(H3Aggregate.bucket_start)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
