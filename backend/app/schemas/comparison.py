from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GpsGapInfo(BaseModel):
    segment_no: int
    gap_before: bool
    missing_length_m: float | None = None


class MatchedSegmentSummary(BaseModel):
    id: UUID
    segment_no: int
    result_state: str
    confidence: float
    geometry: dict[str, object]
    ordered_edge_ids: list[str]
    gap_before: bool
    match_status: str
    reason_code: str | None = None
    processed_at: datetime


class PlannedRouteSummary(BaseModel):
    id: UUID
    route_version: int
    routing_data_version: str
    route_source: str
    valid_from: datetime
    valid_to: datetime | None = None
    geometry: dict[str, object]
    ordered_edge_ids: list[str]


class RouteComparisonResponse(BaseModel):
    trip_id: UUID
    trip_status: str
    started_at: datetime
    ended_at: datetime | None = None
    planned_route: PlannedRouteSummary | None = None
    matched_segments: list[MatchedSegmentSummary] = []
    gps_gaps: list[GpsGapInfo] = []
    total_gaps: int = 0
