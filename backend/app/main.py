import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.adapters.osrm import OsrmClient
from app.adapters.redis_streams import RedisStreams
from app.api.routes import health, planned_routes, trips, version
from app.core.config import get_settings
from app.core.database import Database
from app.core.logging import configure_logging
from app.repositories.readiness import ReadinessRepository
from app.services.readiness import ReadinessService

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    database = Database(settings)
    redis = RedisStreams.from_url(settings.redis_url, settings.redis_stream_name)
    app.state.database = database
    app.state.redis = redis
    app.state.readiness_service = ReadinessService(
        ReadinessRepository(database.engine), redis, OsrmClient(settings.osrm_url)
    )
    yield
    await redis.close()
    await database.close()


app = FastAPI(
    title="Route Deviation Heatmap API",
    version=settings.app_version,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Correlation-ID"],
)
app.include_router(health.router, prefix="/api/v1")
app.include_router(version.router, prefix="/api/v1")
app.include_router(trips.router, prefix="/api/v1")
app.include_router(planned_routes.router, prefix="/api/v1")


@app.middleware("http")
async def correlation_id(request: Request, call_next: object) -> JSONResponse:
    request_id = request.headers.get("X-Correlation-ID", str(uuid4()))
    request.state.correlation_id = request_id
    response = await call_next(request)  # type: ignore[operator]
    response.headers["X-Correlation-ID"] = request_id
    return response  # type: ignore[no-any-return]


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "The request is invalid",
                "correlation_id": request.state.correlation_id,
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"http_{exc.status_code}",
                "message": str(exc.detail),
                "correlation_id": request.state.correlation_id,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled request error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred",
                "correlation_id": request.state.correlation_id,
            }
        },
    )
