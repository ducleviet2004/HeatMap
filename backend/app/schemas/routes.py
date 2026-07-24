from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator


class GeoJsonLineString(BaseModel):
    type: str = "LineString"
    coordinates: list[list[float]]

    @field_validator("coordinates")
    @classmethod
    def validate_linestring(cls, value: list[list[float]]) -> list[list[float]]:
        if len(value) < 2:
            raise ValueError("LineString coordinates must have at least 2 points")
        return value


class PlannedRouteCreate(BaseModel):
    trip_id: UUID
    route_version: int = 1
    routing_data_version: str = "v1"
    route_source: str = "manual"
    geometry: GeoJsonLineString
    valid_from: datetime


class PlannedRouteResponse(BaseModel):
    id: UUID
    trip_id: UUID
    route_version: int
    routing_data_version: str
    route_source: str
    geometry: GeoJsonLineString
    valid_from: datetime
    valid_to: datetime | None = None
    created_at: datetime
