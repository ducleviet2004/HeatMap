"""Schema dung khi so sanh planned route voi actual matched route."""

from enum import StrEnum

from pydantic import BaseModel, Field


class BypassReason(StrEnum):
    """Reason code cho biet missing run co duoc confirm la bypass hay khong."""

    CONFIRMED_BYPASS = "confirmed_bypass"
    ROUTING_VERSION_MISMATCH = "routing_version_mismatch"
    LOW_MATCH_CONFIDENCE = "low_match_confidence"
    BELOW_MINIMUM_LENGTH = "below_minimum_length"
    GPS_GAP = "gps_gap"
    CORRIDOR_DATA_MISSING = "corridor_data_missing"
    SAME_CORRIDOR = "same_corridor"


class PlannedRoadEdge(BaseModel):
    """Planned road edge va metadata can cho BR-02 rules."""

    edge_id: str
    length_m: float = Field(gt=0)
    corridor_distance_m: float | None = Field(default=None, ge=0)
    observed: bool = True


class BypassSegmentResult(BaseModel):
    """Ket qua danh gia mot nhom planned edge bi thieu lien tiep."""

    start_planned_index: int
    end_planned_index: int
    planned_edge_ids: list[str]
    missing_length_m: float
    average_deviation_distance_m: float | None = None
    confirmed: bool
    reason_code: BypassReason
    detection_method: str = "ordered_edge"


class EdgeSequenceComparisonResult(BaseModel):
    """Ket qua so sanh ordered road-edge sequence cua mot route."""

    missing_edge_count: int
    confirmed_bypass_count: int
    bypass_segments: list[BypassSegmentResult]
    planned_routing_data_version: str
    actual_routing_data_version: str
    map_match_confidence: float = Field(ge=0, le=1)
    algorithm_version: str
    threshold_config_version: str
