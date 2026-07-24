import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.adapters.redis_streams import RedisStreams


class FakeRedis:
    def __init__(self) -> None:
        self.fields: dict[str, str] = {}
        self.maxlen: int | None = None
        self.groups: list[str] = []
        self.busygroup_error: bool = False

    async def ping(self) -> bool:
        return True

    async def xinfo_stream(self, _name: str) -> dict[str, Any]:
        return {"length": 10, "groups": len(self.groups)}

    async def xadd(
        self,
        _name: str,
        fields: dict[str, str],
        maxlen: int | None = None,
        approximate: bool = True,
    ) -> str:
        self.fields = fields
        self.maxlen = maxlen
        return "1-0"

    async def xgroup_create(
        self, name: str, id: str = "$", mkstream: bool = True, groupname: str = ""
    ) -> str:
        if self.busygroup_error:
            raise Exception("BUSYGROUP Consumer Group name already exists")
        self.groups.append(groupname)
        return "OK"

    async def xlen(self, _name: str) -> int:
        return 10

    async def aclose(self) -> None:
        return None


async def test_publish_builds_versioned_envelope() -> None:
    client = FakeRedis()
    streams = RedisStreams(client, "events")
    message_id = await streams.publish(
        event_id=UUID("00000000-0000-0000-0000-000000000001"),
        correlation_id="request-1",
        event_type="foundation.test",
        payload={"safe": True},
    )
    assert message_id == "1-0"
    assert client.fields["event_id"] == "00000000-0000-0000-0000-000000000001"
    assert client.fields["payload_version"] == "1"
    assert client.fields["payload"] == '{"safe":true}'
    assert client.maxlen == 100000


async def test_publish_gps_event() -> None:
    client = FakeRedis()
    streams = RedisStreams(client, "route-deviation:events")
    now = datetime.now(UTC)
    message_id = await streams.publish_gps_event(
        event_id=UUID("00000000-0000-0000-0000-000000000002"),
        trip_id=UUID("00000000-0000-0000-0000-000000000010"),
        driver_id=UUID("00000000-0000-0000-0000-000000000020"),
        sequence_no=1,
        recorded_at=now,
        longitude=105.8544,
        latitude=21.0285,
        speed_kmh=42.5,
    )
    assert message_id == "1-0"
    assert client.fields["event_type"] == "gps.event.ingested"

    payload = json.loads(client.fields["payload"])
    assert payload["trip_id"] == "00000000-0000-0000-0000-000000000010"
    assert payload["longitude"] == 105.8544
    assert payload["speed_kmh"] == 42.5


async def test_create_consumer_group_idempotency() -> None:
    client = FakeRedis()
    streams = RedisStreams(client, "route-deviation:events")

    # First creation succeeds
    created = await streams.create_consumer_group("gps-workers")
    assert created is True
    assert "gps-workers" in client.groups

    # Second creation handles BUSYGROUP gracefully
    client.busygroup_error = True
    created_again = await streams.create_consumer_group("gps-workers")
    assert created_again is False


async def test_get_stream_info() -> None:
    client = FakeRedis()
    streams = RedisStreams(client, "route-deviation:events")
    info = await streams.get_stream_info()
    assert info["accessible"] is True
    assert info["length"] == 10
