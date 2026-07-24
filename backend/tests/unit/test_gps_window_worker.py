import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from app.adapters.redis_streams import RedisStreams
from app.services.gps_cleaning import GpsCleaningService
from app.workers.gps_window_worker import GpsWindowWorker


class FakeRedisForWorker:
    def __init__(self) -> None:
        self.acknowledged_ids: list[str] = []
        self.dead_letters: list[dict[str, Any]] = []

    async def ping(self) -> bool:
        return True

    async def xinfo_stream(self, _name: str) -> dict[str, Any]:
        return {"length": 0}

    async def xadd(
        self,
        name: str,
        fields: dict[str, str],
        maxlen: int | None = None,
        approximate: bool = True,
    ) -> str:
        self.dead_letters.append({"stream": name, "fields": fields})
        return "dlq-1-0"

    async def xgroup_create(
        self, name: str, id: str = "$", mkstream: bool = True, groupname: str = ""
    ) -> str:
        return "OK"

    async def xack(self, name: str, groupname: str, *ids: str) -> int:
        self.acknowledged_ids.extend(ids)
        return len(ids)

    async def xlen(self, _name: str) -> int:
        return 0

    async def aclose(self) -> None:
        return None


def create_gps_stream_message(
    msg_id: str,
    trip_id: UUID,
    seq: int,
    accuracy_m: float = 10.0,
    speed_kmh: float = 40.0,
) -> tuple[str, dict[str, str]]:
    event_id = uuid4()
    driver_id = uuid4()
    payload = {
        "event_id": str(event_id),
        "trip_id": str(trip_id),
        "driver_id": str(driver_id),
        "sequence_no": seq,
        "recorded_at": datetime.now(UTC).isoformat(),
        "longitude": 105.85,
        "latitude": 21.02,
        "accuracy_m": accuracy_m,
        "speed_kmh": speed_kmh,
        "heading": 90.0,
    }
    raw_fields = {
        "event_id": str(event_id),
        "correlation_id": f"gps-{trip_id}-{seq}",
        "event_type": "gps.event.ingested",
        "payload": json.dumps(payload),
    }
    return msg_id, raw_fields


async def test_worker_flushes_when_min_batch_size_reached() -> None:
    client = FakeRedisForWorker()
    streams = RedisStreams(client, "route-deviation:events")
    cleaning_service = GpsCleaningService(
        max_accuracy_m=30.0, max_speed_kmh=120.0, threshold_config_version="v1"
    )
    worker = GpsWindowWorker(
        streams=streams,
        cleaning_service=cleaning_service,
        min_batch_size=30,
        flush_interval_sec=10.0,
    )
    await worker.initialize()

    trip_id = uuid4()
    messages: list[tuple[str, dict[str, str]]] = []
    for i in range(1, 31):
        # Point 15 has poor accuracy (50m > 30m threshold)
        acc = 50.0 if i == 15 else 10.0
        messages.append(create_gps_stream_message(f"100-{i}", trip_id, i, accuracy_m=acc))

    results = await worker.process_stream_batch(messages)
    trip_key = str(trip_id)

    assert trip_key in results
    # Total enqueued: 30, Cleaned: 29 (1 filtered out due to accuracy)
    assert len(results[trip_key]) == 29
    assert len(client.acknowledged_ids) == 30


async def test_worker_flushes_on_timer_expiration() -> None:
    client = FakeRedisForWorker()
    streams = RedisStreams(client, "route-deviation:events")
    cleaning_service = GpsCleaningService(
        max_accuracy_m=30.0, max_speed_kmh=120.0, threshold_config_version="v1"
    )
    worker = GpsWindowWorker(
        streams=streams,
        cleaning_service=cleaning_service,
        min_batch_size=30,
        flush_interval_sec=10.0,
    )

    trip_id = uuid4()
    trip_key = str(trip_id)

    # Ingest only 5 points (less than min_batch_size=30)
    for i in range(1, 6):
        msg_id, fields = create_gps_stream_message(f"200-{i}", trip_id, i)
        await worker.ingest_event(msg_id, fields)

    # Initially should not flush
    assert worker.should_flush(trip_key) is False

    # Simulate timer expiration (11 seconds passed)
    future_time = datetime.now(UTC) + timedelta(seconds=11)
    assert worker.should_flush(trip_key, now=future_time) is True

    # Trigger pending flushes
    flushed = await worker.flush_pending_trips(force=True)
    assert len(flushed[trip_key]) == 5
    assert len(client.acknowledged_ids) == 5


async def test_worker_sends_poison_message_to_dlq() -> None:
    client = FakeRedisForWorker()
    streams = RedisStreams(client, "route-deviation:events")
    cleaning_service = GpsCleaningService(
        max_accuracy_m=30.0, max_speed_kmh=120.0, threshold_config_version="v1"
    )
    worker = GpsWindowWorker(streams=streams, cleaning_service=cleaning_service)

    # Corrupted payload (missing trip_id)
    corrupted_fields = {
        "event_id": "invalid-uuid",
        "payload": "invalid-json-content",
    }

    trip_key, envelope = await worker.ingest_event("999-0", corrupted_fields)

    assert trip_key is None
    assert envelope is None
    assert len(client.dead_letters) == 1
    assert client.dead_letters[0]["stream"] == "route-deviation:dead-letter"
    assert "Poison payload" in client.dead_letters[0]["fields"]["error_reason"]
