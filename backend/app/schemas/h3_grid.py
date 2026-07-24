"""Schema cho bước chuyển bypass geometry thành các ô H3."""

from uuid import UUID

from pydantic import BaseModel, Field


class BypassGeometry(BaseModel):
    """Một LineString đã được B03 xác nhận là bypass."""

    coordinates: list[tuple[float, float]] = Field(min_length=2)
    confirmed: bool = True


class TripRouteHexRecord(BaseModel):
    """Bản ghi sẵn sàng để lưu vào bảng trip_route_hexes."""

    trip_id: UUID
    planned_route_id: UUID
    hex_id: str
    h3_resolution: int = Field(ge=9, le=12)
    is_bypass: bool = True
    algorithm_version: str


class H3ConversionResult(BaseModel):
    """Kết quả đã khử trùng lặp theo trip, hex và resolution."""

    records: list[TripRouteHexRecord]

    @property
    def unique_hex_count(self) -> int:
        return len(self.records)
