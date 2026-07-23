import json
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from redis.asyncio import Redis


class RedisLike(Protocol):
    async def ping(self) -> bool: ...
    async def xinfo_stream(self, name: str) -> Any: ...
    async def xadd(self, name: str, fields: dict[str, str]) -> Any: ...
    async def aclose(self) -> None: ...


class RedisStreams:
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
    ) -> str:
        envelope = {
            "event_id": str(event_id),
            "correlation_id": correlation_id,
            "event_type": event_type,
            "occurred_at": datetime.now(UTC).isoformat(),
            "payload_version": payload_version,
            "payload": json.dumps(payload, separators=(",", ":")),
        }
        message_id = await self.client.xadd(self.stream_name, envelope)
        return str(message_id)

    async def close(self) -> None:
        await self.client.aclose()
