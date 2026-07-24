"""Asynchronous GPS Window Worker for batching & cleaning GPS stream events."""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, cast
from uuid import UUID

from app.adapters.redis_streams import RedisStreams
from app.core.config import Settings
from app.services.gps_cleaning import GpsCleaningService

logger = logging.getLogger(__name__)


@dataclass
class GpsPointEnvelope:
    """A structured GPS event parsed from Redis Stream."""

    event_id: UUID
    trip_id: UUID
    driver_id: UUID
    sequence_no: int
    recorded_at: datetime
    longitude: float
    latitude: float
    accuracy_m: float | None
    speed_kmh: float | None
    heading: float | None
    message_id: str


class StreamConsumerLike(Protocol):
    """Protocol matching Redis stream reading & ACK interfaces."""

    async def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        count: int | None = None,
        block: int | None = None,
    ) -> Any: ...

    async def xack(self, name: str, groupname: str, *ids: str) -> Any: ...


class GpsWindowWorker:
    """Async background worker that windows GPS events per trip_id and flushes clean traces."""

    def __init__(
        self,
        *,
        streams: RedisStreams,
        cleaning_service: GpsCleaningService,
        min_batch_size: int = 30,
        max_batch_size: int = 100,
        flush_interval_sec: float = 10.0,
        group_name: str = "gps-cleaning-workers",
        consumer_name: str = "worker-1",
    ) -> None:
        self.streams = streams
        self.cleaning_service = cleaning_service
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.flush_interval_sec = flush_interval_sec
        self.group_name = group_name
        self.consumer_name = consumer_name

        self._buffers: dict[str, list[GpsPointEnvelope]] = {}
        self._last_flush: dict[str, datetime] = {}

    @classmethod
    def from_settings(
        cls,
        streams: RedisStreams,
        cleaning_service: GpsCleaningService,
        settings: Settings,
        consumer_name: str = "worker-1",
    ) -> "GpsWindowWorker":
        return cls(
            streams=streams,
            cleaning_service=cleaning_service,
            min_batch_size=settings.gps_worker_min_batch_size,
            max_batch_size=settings.gps_worker_max_batch_size,
            flush_interval_sec=settings.gps_worker_flush_interval_sec,
            consumer_name=consumer_name,
        )

    async def initialize(self) -> None:
        """Create consumer group idempotently."""
        await self.streams.create_consumer_group(self.group_name)

    def parse_envelope(self, message_id: str, raw_fields: dict[str, str]) -> GpsPointEnvelope:
        """Parse raw Redis fields into GpsPointEnvelope."""
        raw_payload = raw_fields.get("payload", "{}")
        payload = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload

        recorded_at_str = payload.get("recorded_at")
        recorded_at = (
            datetime.fromisoformat(recorded_at_str)
            if isinstance(recorded_at_str, str)
            else datetime.now(UTC)
        )

        acc_m = payload.get("accuracy_m")
        spd_kmh = payload.get("speed_kmh")
        hdg = payload.get("heading")

        return GpsPointEnvelope(
            event_id=UUID(raw_fields.get("event_id", payload.get("event_id"))),
            trip_id=UUID(payload["trip_id"]),
            driver_id=UUID(payload["driver_id"]),
            sequence_no=int(payload["sequence_no"]),
            recorded_at=recorded_at,
            longitude=float(payload["longitude"]),
            latitude=float(payload["latitude"]),
            accuracy_m=float(acc_m) if acc_m is not None else None,
            speed_kmh=float(spd_kmh) if spd_kmh is not None else None,
            heading=float(hdg) if hdg is not None else None,
            message_id=message_id,
        )

    async def ingest_event(
        self, message_id: str, fields: dict[str, str]
    ) -> tuple[str | None, GpsPointEnvelope | None]:
        """Ingest single Redis event into memory buffer or push to DLQ if poison payload."""
        try:
            envelope = self.parse_envelope(message_id, fields)
            trip_key = str(envelope.trip_id)

            if trip_key not in self._buffers:
                self._buffers[trip_key] = []
                self._last_flush[trip_key] = datetime.now(UTC)

            self._buffers[trip_key].append(envelope)
            return trip_key, envelope
        except Exception as exc:
            logger.warning(
                "Failed to parse GPS event message %s. Moving to DLQ. Error: %s",
                message_id,
                exc,
            )
            await self.streams.publish_dead_letter(
                original_message_id=message_id,
                original_stream=self.streams.stream_name,
                error_reason=f"Poison payload parsing error: {exc}",
                attempts=1,
                payload=fields,
            )
            return None, None

    async def flush_trip(self, trip_key: str) -> list[GpsPointEnvelope]:
        """Filter and flush GPS points for a specific trip_id."""
        buffer = self._buffers.get(trip_key, [])
        if not buffer:
            return []

        # Filter clean points using GpsCleaningService
        clean_points = self.cleaning_service.filter_events(buffer)

        # ACK processed messages in Redis Streams
        message_ids = [pt.message_id for pt in buffer]
        client = cast(StreamConsumerLike, self.streams.client)
        await client.xack(self.streams.stream_name, self.group_name, *message_ids)

        # Reset buffer for this trip
        self._buffers[trip_key] = []
        self._last_flush[trip_key] = datetime.now(UTC)

        logger.info(
            "Flushed %d/%d clean GPS points for trip %s",
            len(clean_points),
            len(buffer),
            trip_key,
        )
        return clean_points

    def should_flush(self, trip_key: str, now: datetime | None = None) -> bool:
        """Check if buffer for trip_id meets min batch size or timer expiration."""
        buffer = self._buffers.get(trip_key, [])
        if not buffer:
            return False

        if len(buffer) >= self.min_batch_size or len(buffer) >= self.max_batch_size:
            return True

        current_time = now or datetime.now(UTC)
        last_time = self._last_flush.get(trip_key, current_time)
        elapsed_sec = (current_time - last_time).total_seconds()
        return elapsed_sec >= self.flush_interval_sec

    async def flush_pending_trips(self, force: bool = False) -> dict[str, list[GpsPointEnvelope]]:
        """Check all trip buffers and flush those meeting window or timer criteria."""
        flushed_results: dict[str, list[GpsPointEnvelope]] = {}
        now = datetime.now(UTC)

        for trip_key in list(self._buffers.keys()):
            if force or self.should_flush(trip_key, now=now):
                flushed = await self.flush_trip(trip_key)
                flushed_results[trip_key] = flushed

        return flushed_results

    async def process_stream_batch(
        self, stream_messages: list[tuple[str, dict[str, str]]]
    ) -> dict[str, list[GpsPointEnvelope]]:
        """Ingest a batch of stream messages and trigger flushes for eligible trips."""
        for msg_id, fields in stream_messages:
            await self.ingest_event(msg_id, fields)

        return await self.flush_pending_trips()
