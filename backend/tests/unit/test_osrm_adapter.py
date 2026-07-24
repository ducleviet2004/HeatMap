"""Unit tests for OsrmClient adapter."""

import pytest

from app.adapters.osrm import OsrmClient


@pytest.mark.asyncio
async def test_osrm_client_not_configured() -> None:
    """Verify status when OSRM base URL is None."""
    client = OsrmClient(base_url=None)
    status, detail = await client.status()
    assert status == "not_configured"
    assert detail == "No local routing graph configured"

    route_res = await client.get_route([(105.8, 21.0), (105.81, 21.01)])
    assert route_res is None

    match_res = await client.match_trace([(105.8, 21.0), (105.81, 21.01)])
    assert match_res is None


@pytest.mark.asyncio
async def test_osrm_client_invalid_coordinates_count() -> None:
    """Verify get_route and match_trace return None if less than 2 coordinates provided."""
    client = OsrmClient(base_url="http://localhost:5000")
    route_res = await client.get_route([(105.8, 21.0)])
    assert route_res is None

    match_res = await client.match_trace([])
    assert match_res is None
