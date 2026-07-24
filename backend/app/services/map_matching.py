"""Gui offline GPS trace toi OSRM va chuyen response thanh ket qua de su dung."""

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
from app.services.gps_gap import GpsGapService


class OsrmMatchClient(Protocol):
    """Interface ma MapMatchingService can tu OSRM client."""

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
    """Match GPS trace thanh geometry, ordered road-edge sequence va confidence."""

    def __init__(
        self,
        client: OsrmMatchClient,
        *,
        routing_data_version: str,
        algorithm_version: str,
        gap_service: GpsGapService | None = None,
    ) -> None:
        self.client = client
        self.routing_data_version = routing_data_version
        self.algorithm_version = algorithm_version
        self.gap_service = gap_service or GpsGapService()

    @classmethod
    def from_settings(cls, client: OsrmMatchClient, settings: Settings) -> "MapMatchingService":
        """Lay version va GPS gap threshold tu Settings de ket qua co the audit."""
        return cls(
            client,
            routing_data_version=settings.routing_data_version,
            algorithm_version=settings.algorithm_version,
            gap_service=GpsGapService.from_settings(settings),
        )

    async def match(
        self,
        events: Sequence[GpsEventCreate],
        fallback_levels: Sequence[float] = (50.0, 100.0, 200.0),
    ) -> MapMatchResult:
        """Phan tich GPS gap truoc; long gap duoc match thanh cac trace doc lap."""
        analysis = self.gap_service.analyze(list(events))
        if len(analysis.segments) <= 1:
            # Khong co long gap: gui toan bo trace trong mot OSRM request.
            result = await self._match_segment(events, fallback_levels)
            return result.model_copy(update={"gps_gaps": analysis.gaps})

        partial_results = [
            await self._match_segment(segment, fallback_levels)
            for segment in analysis.segments
            if len(segment) >= 2
        ]
        matched_segments: list[MatchedTraceSegment] = []
        fallback_radiuses: list[float] = []
        for partial in partial_results:
            for segment in partial.segments:
                # Segment sau long gap phai co marker de Frontend khong ve duong noi thang.
                follows_gap = bool(matched_segments)
                matched_segments.append(
                    segment.model_copy(
                        update={
                            "segment_no": len(matched_segments),
                            "gap_before": follows_gap,
                            "reason_code": (
                                "gps_gap_long_split" if follows_gap else segment.reason_code
                            ),
                        }
                    )
                )
            if partial.fallback_radius_m is not None:
                fallback_radiuses.append(partial.fallback_radius_m)

        if not matched_segments:
            return MapMatchResult(
                status=MapMatchStatus.NO_MATCH,
                routing_data_version=self.routing_data_version,
                algorithm_version=self.algorithm_version,
                reason_code="no_match_after_gap_split",
                gps_gaps=analysis.gaps,
            )

        return MapMatchResult(
            status=MapMatchStatus.MATCHED,
            match_confidence=min(segment.match_confidence for segment in matched_segments),
            segments=matched_segments,
            routing_data_version=self.routing_data_version,
            algorithm_version=self.algorithm_version,
            fallback_radius_m=max(fallback_radiuses, default=None),
            gps_gaps=analysis.gaps,
        )

    async def _match_segment(
        self,
        events: Sequence[GpsEventCreate],
        fallback_levels: Sequence[float],
    ) -> MapMatchResult:
        """Map-match GPS events voi Corridor Fallback Check (50m -> 100m -> 200m)."""
        if len(events) < 2:
            return self._empty_result(
                MapMatchStatus.NO_MATCH,
                reason_code="insufficient_trace_points",
            )

        # Khong sort lai vi co the lam sai actual route.
        coordinates = [
            (event.raw_geometry.coordinates[0], event.raw_geometry.coordinates[1])
            for event in events
        ]
        timestamps = self._strict_timestamps(events)
        base_radiuses = self._complete_radiuses(events)

        # Thu raw accuracy truoc, sau do fallback radius 50m, 100m va 200m.
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
                # Validate OSRM response truoc khi doc payload ben trong.
                payload = _OsrmMatchPayload.model_validate(response)
            except ValidationError:
                return self._empty_result(
                    MapMatchStatus.INVALID_RESPONSE,
                    reason_code="invalid_osrm_response",
                )

            if payload.code != "Ok" or not payload.matchings:
                last_reason = payload.code or "NoMatch"
                continue

            # OSRM co the tach trace; giu geometry rieng de khong ve noi qua GPS gap.
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
                # Dung confidence thap nhat de khong che mat segment co match yeu.
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
        """Tao failed result ma khong sinh geometry hoac road edge gia."""
        return MapMatchResult(
            status=status,
            routing_data_version=self.routing_data_version,
            algorithm_version=self.algorithm_version,
            reason_code=reason_code,
        )

    @staticmethod
    def _strict_timestamps(events: Sequence[GpsEventCreate]) -> list[int] | None:
        """Chi gui timestamp khi tat ca gia tri tang dan dung yeu cau cua OSRM."""
        timestamps = [int(event.recorded_at.timestamp()) for event in events]
        if all(
            previous < current
            for previous, current in zip(timestamps, timestamps[1:], strict=False)
        ):
            return timestamps
        return None

    @staticmethod
    def _complete_radiuses(events: Sequence[GpsEventCreate]) -> list[float] | None:
        """Chi gui radius khi moi GPS point deu co accuracy."""
        if any(event.accuracy_m is None for event in events):
            return None
        return [event.accuracy_m for event in events if event.accuracy_m is not None]

    @classmethod
    def _ordered_edges(cls, legs: Sequence[_OsrmLeg]) -> list[MatchedRoadEdge]:
        """Tao directed edge tu tung cap OSRM node lien tiep: ``A->B``."""
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
        """Ghep edge cua leg moi va bo phan OSRM lap tai boundary cua hai leg."""
        maximum_overlap = min(len(existing), len(incoming))
        overlap = next(
            (size for size in range(maximum_overlap, 0, -1) if existing[-size:] == incoming[:size]),
            0,
        )
        existing.extend(incoming[overlap:])
