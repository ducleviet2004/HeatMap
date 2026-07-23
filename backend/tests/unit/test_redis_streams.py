from uuid import UUID

from app.adapters.redis_streams import RedisStreams


class FakeRedis:
    def __init__(self) -> None:
        self.fields: dict[str, str] = {}

    async def ping(self) -> bool:
        return True

    async def xinfo_stream(self, _name: str) -> dict[str, int]:
        return {"length": 0}

    async def xadd(self, _name: str, fields: dict[str, str]) -> str:
        self.fields = fields
        return "1-0"

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
