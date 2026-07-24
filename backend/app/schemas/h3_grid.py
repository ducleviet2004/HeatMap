"""Schema cho buoc convert bypass geometry thanh H3 cell."""

from uuid import UUID

from pydantic import BaseModel, Field


class BypassGeometry(BaseModel):
    """LineString da duoc task B03 confirm la bypass."""

    coordinates: list[tuple[float, float]] = Field(min_length=2)
    confirmed: bool = True


class TripRouteHexRecord(BaseModel):
    """Record san sang de luu vao table trip_route_hexes."""

    trip_id: UUID
    planned_route_id: UUID
    hex_id: str
    h3_resolution: int = Field(ge=9, le=12)
    is_bypass: bool = True
    algorithm_version: str


class H3ConversionResult(BaseModel):
    """Ket qua da deduplicate theo trip, hex va resolution."""

    records: list[TripRouteHexRecord]

    @property
    def unique_hex_count(self) -> int:
        return len(self.records)
