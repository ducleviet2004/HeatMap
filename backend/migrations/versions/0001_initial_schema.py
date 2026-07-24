"""Create the foundation application schema.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "drivers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        *timestamp_columns(),
    )
    op.create_table(
        "trips",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "driver_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drivers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        *timestamp_columns(),
    )
    op.create_index("ix_trips_driver_id", "trips", ["driver_id"])
    op.create_table(
        "planned_routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trip_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trips.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("route_version", sa.Integer(), nullable=False),
        sa.Column("routing_data_version", sa.String(128), nullable=False),
        sa.Column("route_source", sa.String(64), nullable=False),
        sa.Column(
            "geometry",
            geoalchemy2.Geometry("LINESTRING", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column(
            "ordered_edge_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("trip_id", "route_version", name="uq_planned_route_version"),
    )
    op.create_index(
        "ix_planned_routes_geometry",
        "planned_routes",
        ["geometry"],
        postgresql_using="gist",
    )
    op.create_table(
        "gps_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column(
            "trip_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trips.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "driver_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drivers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sequence_no", sa.BigInteger(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "raw_geometry",
            geoalchemy2.Geometry("POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("accuracy_m", sa.Float()),
        sa.Column("speed_kmh", sa.Float()),
        sa.Column("heading", sa.Float()),
        sa.Column(
            "payload_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.UniqueConstraint("trip_id", "sequence_no", name="uq_gps_trip_sequence"),
    )
    op.create_index("ix_gps_driver_recorded", "gps_events", ["driver_id", "recorded_at"])
    op.create_index("ix_gps_recorded_at", "gps_events", ["recorded_at"])
    op.create_index(
        "ix_gps_raw_geometry",
        "gps_events",
        ["raw_geometry"],
        postgresql_using="gist",
    )
    op.create_table(
        "matched_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trip_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trips.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("segment_no", sa.Integer(), nullable=False),
        sa.Column("result_state", sa.String(32), nullable=False),
        sa.Column("routing_data_version", sa.String(128), nullable=False),
        sa.Column("algorithm_version", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "geometry",
            geoalchemy2.Geometry("LINESTRING", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column(
            "ordered_edge_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("gap_before", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("match_status", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(64)),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_matched_segments_trip_id", "matched_segments", ["trip_id"])
    op.create_index(
        "ix_matched_segments_geometry",
        "matched_segments",
        ["geometry"],
        postgresql_using="gist",
    )
    op.create_table(
        "trip_bypass_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trip_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trips.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "planned_route_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("planned_routes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "matched_segment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("matched_segments.id", ondelete="SET NULL"),
        ),
        sa.Column("result_state", sa.String(32), nullable=False),
        sa.Column("detection_method", sa.String(64), nullable=False),
        sa.Column("algorithm_version", sa.String(64), nullable=False),
        sa.Column("threshold_config_version", sa.String(64), nullable=False),
        sa.Column("routing_data_version", sa.String(128), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("missing_length_m", sa.Float(), nullable=False),
        sa.Column("average_deviation_distance_m", sa.Float(), nullable=False),
        sa.Column(
            "geometry",
            geoalchemy2.Geometry("LINESTRING", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("reason_code", sa.String(64)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_trip_bypass_segments_trip_id", "trip_bypass_segments", ["trip_id"])
    op.create_index(
        "ix_trip_bypass_segments_geometry",
        "trip_bypass_segments",
        ["geometry"],
        postgresql_using="gist",
    )
    op.create_table(
        "trip_route_hexes",
        sa.Column(
            "trip_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trips.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "planned_route_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("planned_routes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("hex_id", sa.String(64), nullable=False),
        sa.Column("h3_resolution", sa.SmallInteger(), nullable=False),
        sa.Column("is_bypass", sa.Boolean(), nullable=False),
        sa.Column("algorithm_version", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint(
            "trip_id",
            "planned_route_id",
            "hex_id",
            "h3_resolution",
            "algorithm_version",
            name="pk_trip_route_hexes",
        ),
    )
    op.create_index("ix_trip_route_hexes_hex_res", "trip_route_hexes", ["hex_id", "h3_resolution"])
    op.create_table(
        "h3_aggregates",
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bucket_size", sa.String(32), nullable=False),
        sa.Column("hex_id", sa.String(64), nullable=False),
        sa.Column("h3_resolution", sa.SmallInteger(), nullable=False),
        sa.Column("eligible_trip_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("bypass_trip_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("unique_driver_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("bypass_unique_driver_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("average_deviation_distance_m", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("algorithm_version", sa.String(64), nullable=False),
        sa.Column(
            "refreshed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint(
            "bucket_start",
            "bucket_size",
            "hex_id",
            "h3_resolution",
            "algorithm_version",
            name="pk_h3_aggregates",
        ),
    )
    op.create_index(
        "ix_h3_aggregates_query",
        "h3_aggregates",
        ["hex_id", "h3_resolution", "bucket_start"],
    )


def downgrade() -> None:
    op.drop_table("h3_aggregates")
    op.drop_table("trip_route_hexes")
    op.drop_table("trip_bypass_segments")
    op.drop_table("matched_segments")
    op.drop_table("gps_events")
    op.drop_table("planned_routes")
    op.drop_table("trips")
    op.drop_table("drivers")

