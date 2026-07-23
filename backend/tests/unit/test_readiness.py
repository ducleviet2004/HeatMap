from typing import Literal

import pytest

from app.schemas.status import DependencyState
from app.services.readiness import ReadinessService


class Repository:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    async def database_status(self) -> tuple[bool, bool]:
        if self.fail:
            raise ConnectionError
        return True, True


class Redis:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    async def ping(self) -> bool:
        if self.fail:
            raise ConnectionError
        return True

    async def stream_accessible(self) -> bool:
        return True


class Osrm:
    def __init__(self, state: DependencyState) -> None:
        self.state = state

    async def status(self) -> tuple[DependencyState, str | None]:
        return self.state, None


@pytest.mark.parametrize(
    ("database_failure", "redis_failure", "osrm", "expected"),
    [
        (False, False, "ok", "healthy"),
        (False, False, "not_configured", "degraded"),
        (True, False, "ok", "unavailable"),
        (False, True, "ok", "unavailable"),
    ],
)
async def test_readiness_semantics(
    database_failure: bool,
    redis_failure: bool,
    osrm: DependencyState,
    expected: Literal["healthy", "degraded", "unavailable"],
) -> None:
    service = ReadinessService(
        Repository(fail=database_failure),  # type: ignore[arg-type]
        Redis(fail=redis_failure),  # type: ignore[arg-type]
        Osrm(osrm),  # type: ignore[arg-type]
    )
    result = await service.check()
    assert result.status == expected
