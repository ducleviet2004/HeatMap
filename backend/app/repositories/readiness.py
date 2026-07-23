from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


class ReadinessRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def database_status(self) -> tuple[bool, bool]:
        async with self.engine.connect() as connection:
            database_ok = (await connection.execute(text("SELECT 1"))).scalar_one() == 1
            postgis_ok = (
                await connection.execute(
                    text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='postgis')")
                )
            ).scalar_one()
        return database_ok, bool(postgis_ok)
