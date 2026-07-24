"""Các schema kết quả của OSRM Map Matching."""

from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.routes import GeoJsonLineString


class MapMatchStatus(StrEnum):
    """Trạng thái của một lần map matching."""

    MATCHED = "matched"
    NO_MATCH = "no_match"
    UNAVAILABLE = "unavailable"
    INVALID_RESPONSE = "invalid_response"


class MatchedRoadEdge(BaseModel):
    """Một đoạn đường có hướng, ví dụ node ``A->B``."""

    edge_id: str
    from_node_id: int
    to_node_id: int


class MatchedTraceSegment(BaseModel):
    """Một đoạn trace liên tục mà OSRM match được."""

    segment_no: int
    match_confidence: float = Field(ge=0.0, le=1.0)
    geometry: GeoJsonLineString
    ordered_road_edges: list[MatchedRoadEdge]


class MapMatchResult(BaseModel):
    """Kết quả map matching của toàn bộ offline trace."""

    status: MapMatchStatus
    match_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    segments: list[MatchedTraceSegment] = Field(default_factory=list)
    unmatched_point_indices: list[int] = Field(default_factory=list)
    routing_data_version: str
    algorithm_version: str
    reason_code: str | None = None
