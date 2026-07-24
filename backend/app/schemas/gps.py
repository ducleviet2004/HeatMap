from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class GeoJsonPoint(BaseModel):
    type: str = "Point"
    coordinates: list[float]

    @field_validator("coordinates")
    @classmethod
    def validate_point(cls, value: list[float]) -> list[float]:
        if len(value) != 2:
            raise ValueError("Point coordinates must have exactly 2 elements [longitude, latitude]")
        return value


class GpsEventCreate(BaseModel):
    event_id: UUID
    trip_id: UUID
    driver_id: UUID
    sequence_no: int
    recorded_at: datetime
    raw_geometry: GeoJsonPoint
    accuracy_m: float | None = None
    speed_kmh: float | None = None
    heading: float | None = None
    payload_metadata: dict[str, object] = Field(default_factory=dict)


class GpsEventResponse(BaseModel):
    id: int
    event_id: UUID
    trip_id: UUID
    driver_id: UUID
    sequence_no: int
    recorded_at: datetime
    received_at: datetime
    raw_geometry: GeoJsonPoint
    accuracy_m: float | None = None
    speed_kmh: float | None = None
    heading: float | None = None
    payload_metadata: dict[str, object]
