"""Gửi offline GPS trace tới OSRM và chuyển response thành kết quả dễ sử dụng."""

from collections.abc import Sequence
from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError

from app.core.config import Settings
from app.schemas.gps import GpsEventCreate
from app.schemas.map_matching import (
    MapMatchResult,
    MapMatchStatus,
    MatchedRoadEdge,
    MatchedTraceSegment,
)
from app.schemas.routes import GeoJsonLineString


class OsrmMatchClient(Protocol):
    """Các tham số MapMatchingService cần từ OSRM client."""

    async def match_trace(
        self,
        coordinates: list[tuple[float, float]],
        timestamps: list[int] | None = None,
        radiuses: list[float] | None = None,
        overview: str = "full",
        geometries: str = "geojson",
    ) -> dict[str, Any] | None: ...


class _OsrmAnnotation(BaseModel):
    nodes: list[int] = Field(default_factory=list)


class _OsrmLeg(BaseModel):
    annotation: _OsrmAnnotation


class _OsrmGeometry(BaseModel):
    type: str
    coordinates: list[list[float]]


class _OsrmMatching(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)
    geometry: _OsrmGeometry
    legs: list[_OsrmLeg]


class _OsrmMatchPayload(BaseModel):
    code: str
    matchings: list[_OsrmMatching] = Field(default_factory=list)
    tracepoints: list[dict[str, Any] | None] = Field(default_factory=list)


class MapMatchingService:
    """Match chuỗi GPS thành geometry, road-edge sequence và confidence."""

    def __init__(
        self,
        client: OsrmMatchClient,
        *,
        routing_data_version: str,
        algorithm_version: str,
    ) -> None:
        self.client = client
        self.routing_data_version = routing_data_version
        self.algorithm_version = algorithm_version

    @classmethod
    def from_settings(cls, client: OsrmMatchClient, settings: Settings) -> "MapMatchingService":
        """Lấy version từ Settings để kết quả có thể kiểm tra lại sau này."""
        return cls(
            client,
            routing_data_version=settings.routing_data_version,
            algorithm_version=settings.algorithm_version,
        )

    async def match(
        self,
        events: Sequence[GpsEventCreate],
        fallback_levels: Sequence[float] = (50.0, 100.0, 200.0),
    ) -> MapMatchResult:
        """Map-match các GPS event với cơ chế Corridor Fallback Check (50m -> 100m -> 200m)."""
        if len(events) < 2:
            return self._empty_result(
                MapMatchStatus.NO_MATCH,
                reason_code="insufficient_trace_points",
            )

        # Không sort lại vì có thể làm sai tuyến đường thực tế.
        coordinates = [
            (event.raw_geometry.coordinates[0], event.raw_geometry.coordinates[1])
            for event in events
        ]
        timestamps = self._strict_timestamps(events)
        base_radiuses = self._complete_radiuses(events)

        # Danh sách các nấc radiuses thử nghiệm: Dữ liệu thực tế trước, sau đó là 50m, 100m, 200m
        radius_attempts: list[tuple[float | None, list[float] | None]] = [(None, base_radiuses)]

        for level in fallback_levels:
            radius_attempts.append((level, [level] * len(events)))

        last_reason = "NoMatch"

        for fallback_radius, candidate_radiuses in radius_attempts:
            response = await self.client.match_trace(
                coordinates,
                timestamps=timestamps,
                radiuses=candidate_radiuses,
                overview="full",
                geometries="geojson",
            )

            if response is None:
                return self._empty_result(
                    MapMatchStatus.UNAVAILABLE,
                    reason_code="osrm_unavailable",
                )

            try:
                # Kiểm tra cấu trúc response trước khi đọc dữ liệu bên trong.
                payload = _OsrmMatchPayload.model_validate(response)
            except ValidationError:
                return self._empty_result(
                    MapMatchStatus.INVALID_RESPONSE,
                    reason_code="invalid_osrm_response",
                )

            if payload.code != "Ok" or not payload.matchings:
                last_reason = payload.code or "NoMatch"
                continue

            # OSRM có thể tách trace khi gặp GPS gap; không nối các segment này lại với nhau.
            segments = [
                MatchedTraceSegment(
                    segment_no=index,
                    match_confidence=matching.confidence,
                    geometry=GeoJsonLineString(
                        type=matching.geometry.type,
                        coordinates=matching.geometry.coordinates,
                    ),
                    ordered_road_edges=self._ordered_edges(matching.legs),
                )
                for index, matching in enumerate(payload.matchings)
            ]
            unmatched_indices = [
                index for index, tracepoint in enumerate(payload.tracepoints) if tracepoint is None
            ]

            return MapMatchResult(
                status=MapMatchStatus.MATCHED,
                # Dùng confidence thấp nhất để không bỏ qua một segment có kết quả match yếu.
                match_confidence=min(segment.match_confidence for segment in segments),
                segments=segments,
                unmatched_point_indices=unmatched_indices,
                routing_data_version=self.routing_data_version,
                algorithm_version=self.algorithm_version,
                fallback_radius_m=fallback_radius,
            )

        return self._empty_result(
            MapMatchStatus.NO_MATCH,
            reason_code=last_reason,
        )

    def _empty_result(self, status: MapMatchStatus, *, reason_code: str) -> MapMatchResult:
        """Tạo kết quả không thành công mà không sinh geometry hoặc edge giả."""
        return MapMatchResult(
            status=status,
            routing_data_version=self.routing_data_version,
            algorithm_version=self.algorithm_version,
            reason_code=reason_code,
        )

    @staticmethod
    def _strict_timestamps(events: Sequence[GpsEventCreate]) -> list[int] | None:
        """Chỉ gửi timestamp khi tất cả giá trị tăng dần đúng yêu cầu của OSRM."""
        timestamps = [int(event.recorded_at.timestamp()) for event in events]
        if all(
            previous < current
            for previous, current in zip(timestamps, timestamps[1:], strict=False)
        ):
            return timestamps
        return None

    @staticmethod
    def _complete_radiuses(events: Sequence[GpsEventCreate]) -> list[float] | None:
        """Chỉ gửi radius khi mọi GPS point đều có accuracy."""
        if any(event.accuracy_m is None for event in events):
            return None
        return [event.accuracy_m for event in events if event.accuracy_m is not None]

    @classmethod
    def _ordered_edges(cls, legs: Sequence[_OsrmLeg]) -> list[MatchedRoadEdge]:
        """Tạo edge có hướng từ từng cặp OSRM node liên tiếp: ``A->B``."""
        ordered_edges: list[MatchedRoadEdge] = []
        for leg in legs:
            leg_edges = [
                MatchedRoadEdge(
                    edge_id=f"{from_node_id}->{to_node_id}",
                    from_node_id=from_node_id,
                    to_node_id=to_node_id,
                )
                for from_node_id, to_node_id in zip(
                    leg.annotation.nodes,
                    leg.annotation.nodes[1:],
                    strict=False,
                )
                if from_node_id != to_node_id
            ]
            cls._append_without_boundary_overlap(ordered_edges, leg_edges)
        return ordered_edges

    @staticmethod
    def _append_without_boundary_overlap(
        existing: list[MatchedRoadEdge],
        incoming: list[MatchedRoadEdge],
    ) -> None:
        """Nối edge của leg mới và bỏ phần bị OSRM lặp lại ở ranh giới hai leg."""
        maximum_overlap = min(len(existing), len(incoming))
        overlap = next(
            (size for size in range(maximum_overlap, 0, -1) if existing[-size:] == incoming[:size]),
            0,
        )
        existing.extend(incoming[overlap:])
