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
        return cls(
            client,
            routing_data_version=settings.routing_data_version,
            algorithm_version=settings.algorithm_version,
        )

    async def match(self, events: Sequence[GpsEventCreate]) -> MapMatchResult:
        if len(events) < 2:
            return self._empty_result(
                MapMatchStatus.NO_MATCH,
                reason_code="insufficient_trace_points",
            )

        coordinates = [
            (event.raw_geometry.coordinates[0], event.raw_geometry.coordinates[1])
            for event in events
        ]
        timestamps = self._strict_timestamps(events)
        radiuses = self._complete_radiuses(events)
        response = await self.client.match_trace(
            coordinates,
            timestamps=timestamps,
            radiuses=radiuses,
            overview="full",
            geometries="geojson",
        )

        if response is None:
            return self._empty_result(
                MapMatchStatus.UNAVAILABLE,
                reason_code="osrm_unavailable",
            )

        try:
            payload = _OsrmMatchPayload.model_validate(response)
        except ValidationError:
            return self._empty_result(
                MapMatchStatus.INVALID_RESPONSE,
                reason_code="invalid_osrm_response",
            )

        if payload.code != "Ok" or not payload.matchings:
            return self._empty_result(
                MapMatchStatus.NO_MATCH,
                reason_code=payload.code,
            )

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
            match_confidence=min(segment.match_confidence for segment in segments),
            segments=segments,
            unmatched_point_indices=unmatched_indices,
            routing_data_version=self.routing_data_version,
            algorithm_version=self.algorithm_version,
        )

    def _empty_result(self, status: MapMatchStatus, *, reason_code: str) -> MapMatchResult:
        return MapMatchResult(
            status=status,
            routing_data_version=self.routing_data_version,
            algorithm_version=self.algorithm_version,
            reason_code=reason_code,
        )

    @staticmethod
    def _strict_timestamps(events: Sequence[GpsEventCreate]) -> list[int] | None:
        timestamps = [int(event.recorded_at.timestamp()) for event in events]
        if all(
            previous < current
            for previous, current in zip(timestamps, timestamps[1:], strict=False)
        ):
            return timestamps
        return None

    @staticmethod
    def _complete_radiuses(events: Sequence[GpsEventCreate]) -> list[float] | None:
        if any(event.accuracy_m is None for event in events):
            return None
        return [event.accuracy_m for event in events if event.accuracy_m is not None]

    @classmethod
    def _ordered_edges(cls, legs: Sequence[_OsrmLeg]) -> list[MatchedRoadEdge]:
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
        maximum_overlap = min(len(existing), len(incoming))
        overlap = next(
            (size for size in range(maximum_overlap, 0, -1) if existing[-size:] == incoming[:size]),
            0,
        )
        existing.extend(incoming[overlap:])
