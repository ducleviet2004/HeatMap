import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.adapters.redis_streams import RedisStreams

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="requires real PostgreSQL/PostGIS and Redis",
)


async def test_postgis_schema_and_idempotency_constraints() -> None:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    try:
        async with engine.connect() as connection:
            postgis = await connection.scalar(text("SELECT postgis_version()"))
            tables = (
                await connection.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema='public' AND table_name IN "
                        "('drivers','trips','planned_routes','gps_events')"
                    )
                )
            ).scalars()
            constraints = (
                await connection.execute(
                    text(
                        "SELECT constraint_name FROM information_schema.table_constraints "
                        "WHERE constraint_schema='public' AND constraint_name IN "
                        "('uq_planned_route_version','uq_gps_trip_sequence')"
                    )
                )
            ).scalars()
        assert postgis
        assert set(tables) == {"drivers", "trips", "planned_routes", "gps_events"}
        assert set(constraints) == {"uq_planned_route_version", "uq_gps_trip_sequence"}
    finally:
        await engine.dispose()


async def test_real_redis_stream_publish() -> None:
    stream_name = f"route-deviation:test:{uuid4()}"
    streams = RedisStreams.from_url(os.environ["REDIS_URL"], stream_name)
    try:
        message_id = await streams.publish(
            event_id=uuid4(),
            correlation_id="integration-test",
            event_type="foundation.integration",
            payload={"synthetic": True},
        )
        assert message_id
        assert await streams.ping()
        assert await streams.stream_accessible()
    finally:
        await streams.client.delete(stream_name)  # type: ignore[attr-defined]
        await streams.close()
