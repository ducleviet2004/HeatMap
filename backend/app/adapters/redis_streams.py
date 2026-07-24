import json
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from redis.asyncio import Redis


class RedisLike(Protocol):
    async def ping(self) -> bool: ...
    async def xinfo_stream(self, name: str) -> Any: ...
    async def xadd(
        self,
        name: str,
        fields: dict[str, str],
        maxlen: int | None = None,
        approximate: bool = True,
    ) -> Any: ...
    async def xgroup_create(
        self, name: str, id: str = "$", mkstream: bool = True, groupname: str = ""
    ) -> Any: ...
    async def xlen(self, name: str) -> int: ...
    async def aclose(self) -> None: ...


class RedisStreams:
    """Redis Streams adapter acting as a durable queue for GPS ingestion & background workers."""

    def __init__(self, client: RedisLike, stream_name: str) -> None:
        self.client = client
        self.stream_name = stream_name

    @classmethod
    def from_url(cls, url: str, stream_name: str) -> "RedisStreams":
        return cls(Redis.from_url(url, decode_responses=True), stream_name)

    async def ping(self) -> bool:
        return bool(await self.client.ping())

    async def stream_accessible(self) -> bool:
        try:
            await self.client.xinfo_stream(self.stream_name)
        except Exception as exc:
            if "no such key" not in str(exc).lower():
                raise
        return True

    async def publish(
        self,
        *,
        event_id: UUID,
        correlation_id: str,
        event_type: str,
        payload: dict[str, Any],
        payload_version: str = "1",
        maxlen: int | None = 100000,
    ) -> str:
        """Publish a generic domain event envelope into Redis Stream."""
        envelope = {
            "event_id": str(event_id),
            "correlation_id": correlation_id,
            "event_type": event_type,
            "occurred_at": datetime.now(UTC).isoformat(),
            "payload_version": payload_version,
            "payload": json.dumps(payload, separators=(",", ":")),
        }
        message_id = await self.client.xadd(
            self.stream_name, envelope, maxlen=maxlen, approximate=True
        )
        return str(message_id)

    async def publish_gps_event(
        self,
        *,
        event_id: UUID,
        trip_id: UUID,
        driver_id: UUID,
        sequence_no: int,
        recorded_at: datetime,
        longitude: float,
        latitude: float,
        accuracy_m: float | None = None,
        speed_kmh: float | None = None,
        heading: float | None = None,
        correlation_id: str = "",
        maxlen: int | None = 100000,
    ) -> str:
        """Publish a structured GPS ingestion event into Redis Stream."""
        payload = {
            "trip_id": str(trip_id),
            "driver_id": str(driver_id),
            "sequence_no": sequence_no,
            "recorded_at": recorded_at.isoformat(),
            "longitude": longitude,
            "latitude": latitude,
            "accuracy_m": accuracy_m,
            "speed_kmh": speed_kmh,
            "heading": heading,
        }
        return await self.publish(
            event_id=event_id,
            correlation_id=correlation_id or f"gps-{trip_id}-{sequence_no}",
            event_type="gps.event.ingested",
            payload=payload,
            payload_version="1",
            maxlen=maxlen,
        )

    async def create_consumer_group(
        self, group_name: str, start_id: str = "$", mkstream: bool = True
    ) -> bool:
        """Create a Redis Stream consumer group idempotently (ignores BUSYGROUP error)."""
        try:
            await self.client.xgroup_create(
                name=self.stream_name, id=start_id, mkstream=mkstream, groupname=group_name
            )
            return True
        except Exception as exc:
            if "busygroup" in str(exc).lower():
                return False
            raise

    async def get_stream_info(self) -> dict[str, Any]:
        """Fetch stream status, length, and metadata for telemetry."""
        try:
            info = await self.client.xinfo_stream(self.stream_name)
            length = await self.client.xlen(self.stream_name)
            return {
                "accessible": True,
                "length": length,
                "info": info if isinstance(info, dict) else {},
            }
        except Exception as exc:
            if "no such key" in str(exc).lower():
                return {"accessible": True, "length": 0, "info": {}}
            return {"accessible": False, "length": 0, "error": str(exc)}

    async def close(self) -> None:
        await self.client.aclose()
