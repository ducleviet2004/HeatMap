"""Schema cho raw GPS data, GPS Cleaning va GPS Gap."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class GpsRejectionReason(StrEnum):
    """Reason code cho GPS point bi cleaning filter reject."""

    POOR_ACCURACY = "poor_accuracy"
    EXCESSIVE_SPEED = "excessive_speed"


class GpsGapReason(StrEnum):
    """Reason code phan loai khoang thoi gian khong nhan duoc GPS."""

    SHORT_GAP = "gps_gap_short"
    MEDIUM_GAP = "gps_gap_medium"
    LONG_GAP_SPLIT = "gps_gap_long_split"


class GpsGapRecord(BaseModel):
    """Thong tin GPS gap giua hai point lien tiep."""

    before_sequence_no: int
    after_sequence_no: int
    duration_seconds: float = Field(gt=0)
    reason_code: GpsGapReason
    split_segment: bool


class GpsCleaningResult(BaseModel):
    """Ket qua quality check cua mot GPS point."""

    accepted: bool
    reasons: tuple[GpsRejectionReason, ...] = ()
    threshold_config_version: str


class GeoJsonPoint(BaseModel):
    """GeoJSON Point co format ``[longitude, latitude]``."""

    type: str = "Point"
    coordinates: list[float]

    @field_validator("coordinates")
    @classmethod
    def validate_point(cls, value: list[float]) -> list[float]:
        if len(value) != 2:
            raise ValueError("Point coordinates must have exactly 2 elements [longitude, latitude]")
        return value


class GpsEventCreate(BaseModel):
    """Raw GPS event duoc gui vao he thong."""

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
    """Raw GPS event tra ve sau khi luu database."""

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
