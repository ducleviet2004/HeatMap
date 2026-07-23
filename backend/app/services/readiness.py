from app.adapters.osrm import OsrmClient
from app.adapters.redis_streams import RedisStreams
from app.repositories.readiness import ReadinessRepository
from app.schemas.status import DependencyStatus, ReadinessResponse


class ReadinessService:
    def __init__(
        self,
        repository: ReadinessRepository,
        redis: RedisStreams,
        osrm: OsrmClient,
    ) -> None:
        self.repository = repository
        self.redis = redis
        self.osrm = osrm

    async def check(self) -> ReadinessResponse:
        dependencies: dict[str, DependencyStatus] = {}
        try:
            database_ok, postgis_ok = await self.repository.database_status()
            dependencies["database"] = DependencyStatus(
                status="ok" if database_ok else "unavailable"
            )
            dependencies["postgis"] = DependencyStatus(
                status="ok" if postgis_ok else "unavailable",
                detail=None if postgis_ok else "PostGIS extension is missing",
            )
        except Exception:
            dependencies["database"] = DependencyStatus(
                status="unavailable", detail="Database is unavailable"
            )
            dependencies["postgis"] = DependencyStatus(
                status="unavailable", detail="PostGIS could not be checked"
            )

        try:
            redis_ok = await self.redis.ping()
            stream_ok = await self.redis.stream_accessible()
            dependencies["redis"] = DependencyStatus(status="ok" if redis_ok else "unavailable")
            dependencies["redis_stream"] = DependencyStatus(
                status="ok" if stream_ok else "unavailable"
            )
        except Exception:
            dependencies["redis"] = DependencyStatus(
                status="unavailable", detail="Redis is unavailable"
            )
            dependencies["redis_stream"] = DependencyStatus(
                status="unavailable", detail="Redis Stream could not be checked"
            )

        osrm_status, osrm_detail = await self.osrm.status()
        dependencies["osrm"] = DependencyStatus(status=osrm_status, detail=osrm_detail)

        required = [
            dependencies[key].status for key in ("database", "postgis", "redis", "redis_stream")
        ]
        if "unavailable" in required:
            overall = "unavailable"
        elif dependencies["osrm"].status != "ok":
            overall = "degraded"
        else:
            overall = "healthy"
        return ReadinessResponse(status=overall, dependencies=dependencies)
