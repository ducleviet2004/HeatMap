from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.dependencies import get_gps_ingestion_service
from app.main import app

NOW = datetime.now(UTC)
UUID1 = UUID("00000000-0000-0000-0000-000000000001")
UUID2 = UUID("00000000-0000-0000-0000-000000000002")

VALID_PAYLOAD = {
    "event_id": str(UUID1),
    "trip_id": str(UUID2),
    "driver_id": str(UUID1),
    "sequence_no": 1,
    "recorded_at": NOW.isoformat(),
    "raw_geometry": {"type": "Point", "coordinates": [105.85, 21.03]},
    "accuracy_m": 5.0,
    "speed_kmh": 60.0,
}


class StubIngestionService:
    async def ingest(self, data: object, correlation_id: str = "") -> bool:
        return True


@asynccontextmanager
async def no_lifespan(_app: object) -> AsyncIterator[None]:
    yield


app.router.lifespan_context = no_lifespan
app.dependency_overrides[get_gps_ingestion_service] = lambda: StubIngestionService()


def test_ingest_gps_event_returns_ack() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/gps/events", json=VALID_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["event_id"] == str(UUID1)


def test_ingest_gps_event_validation_error() -> None:
    payload = dict(VALID_PAYLOAD)
    payload.pop("event_id")
    with TestClient(app) as client:
        response = client.post("/api/v1/gps/events", json=payload)
    assert response.status_code == 422


def test_ingest_gps_event_correlation_id() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/gps/events",
            json=VALID_PAYLOAD,
            headers={"X-Correlation-ID": "test-correlation"},
        )
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == "test-correlation"
