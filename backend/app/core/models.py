"""SQLAlchemy 2.0 ORM Models for Route Deviation Heatmap Analytics System (PRD V4)."""

import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )


class Driver(Base, TimestampMixin):
    """Driver entity representing registered vehicle operators."""

    __tablename__ = "drivers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    external_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    trips: Mapped[list["Trip"]] = relationship("Trip", back_populates="driver")


class Trip(Base, TimestampMixin):
    """Trip entity representing a single vehicle voyage."""

    __tablename__ = "trips"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    external_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drivers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    driver: Mapped["Driver"] = relationship("Driver", back_populates="trips")
    planned_routes: Mapped[list["PlannedRoute"]] = relationship(
        "PlannedRoute", back_populates="trip"
    )
    gps_events: Mapped[list["GPSEvent"]] = relationship("GPSEvent", back_populates="trip")
    matched_segments: Mapped[list["MatchedSegment"]] = relationship(
        "MatchedSegment", back_populates="trip"
    )
    bypass_segments: Mapped[list["TripBypassSegment"]] = relationship(
        "TripBypassSegment", back_populates="trip"
    )


class PlannedRoute(Base):
    """Planned route LineString geometry and expected road-edge sequence."""

    __tablename__ = "planned_routes"
    __table_args__ = (
        UniqueConstraint("trip_id", "route_version", name="uq_planned_route_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False
    )
    route_version: Mapped[int] = mapped_column(Integer, nullable=False)
    routing_data_version: Mapped[str] = mapped_column(String(128), nullable=False)
    route_source: Mapped[str] = mapped_column(String(64), nullable=False)
    geometry: Mapped[Any] = mapped_column(
        Geometry("LINESTRING", srid=4326, spatial_index=False), nullable=False
    )
    ordered_edge_ids: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    valid_from: Mapped[datetime] = mapped_column(nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(), nullable=False
    )

    trip: Mapped["Trip"] = relationship("Trip", back_populates="planned_routes")


class GPSEvent(Base):
    """Immutable raw GPS event coordinates recorded during a trip."""

    __tablename__ = "gps_events"
    __table_args__ = (
        UniqueConstraint("trip_id", "sequence_no", name="uq_gps_trip_sequence"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="RESTRICT"), nullable=False
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False
    )
    sequence_no: Mapped[int] = mapped_column(BigInteger, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(), nullable=False
    )
    raw_geometry: Mapped[Any] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=False), nullable=False
    )
    accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    trip: Mapped["Trip"] = relationship("Trip", back_populates="gps_events")


class MatchedSegment(Base):
    """Matched road-edge sequence and matched trace from OSRM map-matching."""

    __tablename__ = "matched_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    segment_no: Mapped[int] = mapped_column(Integer, nullable=False)
    result_state: Mapped[str] = mapped_column(String(32), nullable=False)
    routing_data_version: Mapped[str] = mapped_column(String(128), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    geometry: Mapped[Any] = mapped_column(
        Geometry("LINESTRING", srid=4326, spatial_index=False), nullable=False
    )
    ordered_edge_ids: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    gap_before: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    match_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    processed_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(), nullable=False
    )

    trip: Mapped["Trip"] = relationship("Trip", back_populates="matched_segments")


class TripBypassSegment(Base):
    """Confirmed bypassed segment of a planned route."""

    __tablename__ = "trip_bypass_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    planned_route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("planned_routes.id", ondelete="CASCADE"),
        nullable=False,
    )
    matched_segment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matched_segments.id", ondelete="SET NULL"),
        nullable=True,
    )
    result_state: Mapped[str] = mapped_column(String(32), nullable=False)
    detection_method: Mapped[str] = mapped_column(String(64), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(64), nullable=False)
    threshold_config_version: Mapped[str] = mapped_column(String(64), nullable=False)
    routing_data_version: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    missing_length_m: Mapped[float] = mapped_column(Float, nullable=False)
    average_deviation_distance_m: Mapped[float] = mapped_column(Float, nullable=False)
    geometry: Mapped[Any] = mapped_column(
        Geometry("LINESTRING", srid=4326, spatial_index=False), nullable=False
    )
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(), nullable=False
    )

    trip: Mapped["Trip"] = relationship("Trip", back_populates="bypass_segments")


class TripRouteHex(Base):
    """Mapping of trip planned routes and bypass segments to H3 Spatial Grid."""

    __tablename__ = "trip_route_hexes"
    __table_args__ = (
        PrimaryKeyConstraint(
            "trip_id",
            "planned_route_id",
            "hex_id",
            "h3_resolution",
            "algorithm_version",
            name="pk_trip_route_hexes",
        ),
    )

    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False
    )
    planned_route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("planned_routes.id", ondelete="CASCADE"),
        nullable=False,
    )
    hex_id: Mapped[str] = mapped_column(String(64), nullable=False)
    h3_resolution: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_bypass: Mapped[bool] = mapped_column(Boolean, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(), nullable=False
    )


class H3Aggregate(Base):
    """Pre-aggregated heat map analytics by time bucket and H3 resolution."""

    __tablename__ = "h3_aggregates"
    __table_args__ = (
        PrimaryKeyConstraint(
            "bucket_start",
            "bucket_size",
            "hex_id",
            "h3_resolution",
            "algorithm_version",
            name="pk_h3_aggregates",
        ),
    )

    bucket_start: Mapped[datetime] = mapped_column(nullable=False)
    bucket_size: Mapped[str] = mapped_column(String(32), nullable=False)
    hex_id: Mapped[str] = mapped_column(String(64), nullable=False)
    h3_resolution: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    eligible_trip_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0"
    )
    bypass_trip_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0"
    )
    unique_driver_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0"
    )
    bypass_unique_driver_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0"
    )
    average_deviation_distance_m: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.0"
    )
    algorithm_version: Mapped[str] = mapped_column(String(64), nullable=False)
    refreshed_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(), nullable=False
    )
