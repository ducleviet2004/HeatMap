"""Các schema dùng khi so sánh planned route với actual matched route."""

from enum import StrEnum

from pydantic import BaseModel, Field


class BypassReason(StrEnum):
    """Lý do một missing edge run được hoặc không được xác nhận là bypass."""

    CONFIRMED_BYPASS = "confirmed_bypass"
    ROUTING_VERSION_MISMATCH = "routing_version_mismatch"
    LOW_MATCH_CONFIDENCE = "low_match_confidence"
    BELOW_MINIMUM_LENGTH = "below_minimum_length"
    GPS_GAP = "gps_gap"
    CORRIDOR_DATA_MISSING = "corridor_data_missing"
    SAME_CORRIDOR = "same_corridor"


class PlannedRoadEdge(BaseModel):
    """Một edge của planned route cùng dữ liệu cần cho các rule BR-02."""

    edge_id: str
    length_m: float = Field(gt=0)
    corridor_distance_m: float | None = Field(default=None, ge=0)
    observed: bool = True


class BypassSegmentResult(BaseModel):
    """Kết quả đánh giá một nhóm planned edge bị thiếu liên tiếp."""

    start_planned_index: int
    end_planned_index: int
    planned_edge_ids: list[str]
    missing_length_m: float
    average_deviation_distance_m: float | None = None
    confirmed: bool
    reason_code: BypassReason
    detection_method: str = "ordered_edge"


class EdgeSequenceComparisonResult(BaseModel):
    """Kết quả so sánh ordered road-edge sequence của một route."""

    missing_edge_count: int
    confirmed_bypass_count: int
    bypass_segments: list[BypassSegmentResult]
    planned_routing_data_version: str
    actual_routing_data_version: str
    map_match_confidence: float = Field(ge=0, le=1)
    algorithm_version: str
    threshold_config_version: str
