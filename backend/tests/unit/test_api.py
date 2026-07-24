from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from app.api.dependencies import get_readiness_service
from app.main import app
from app.schemas.status import DependencyStatus, ReadinessResponse


class StubReadiness:
    async def check(self) -> ReadinessResponse:
        return ReadinessResponse(
            status="degraded",
            dependencies={
                "database": DependencyStatus(status="ok"),
                "postgis": DependencyStatus(status="ok"),
                "redis": DependencyStatus(status="ok"),
                "redis_stream": DependencyStatus(status="ok"),
                "osrm": DependencyStatus(status="not_configured"),
            },
        )


@asynccontextmanager
async def no_lifespan(_app: object) -> AsyncIterator[None]:
    yield


app.router.lifespan_context = no_lifespan
app.dependency_overrides[get_readiness_service] = lambda: StubReadiness()


def test_health_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "route-deviation-api",
        "version": "0.1.0",
    }
    assert response.headers["X-Correlation-ID"]


def test_readiness_degraded_semantics() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["dependencies"]["osrm"]["status"] == "not_configured"


def test_version_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/version")
    body = response.json()
    assert response.status_code == 200
    assert body["application"] == "0.1.0"
    assert body["algorithm"] == "unimplemented"
    assert body["routing_data"] == "not_configured"


def test_heatmap_empty_feature_collection() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/heatmap")
    body = response.json()
    assert response.status_code == 200
    assert body["type"] == "FeatureCollection"
    assert isinstance(body["features"], list)


def test_error_contract_does_not_expose_stack_trace() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/not-a-real-endpoint")
    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "http_404",
        "message": "Not Found",
        "correlation_id": response.headers["X-Correlation-ID"],
    }
