import httpx


class OsrmClient:
    def __init__(self, base_url: str | None) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None

    async def status(self) -> tuple[str, str | None]:
        if not self.base_url:
            return "not_configured", "No local routing graph configured"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.base_url}/route/v1/driving/0,0;0,0")
            if response.status_code in {200, 400}:
                return "ok", None
            return "degraded", f"OSRM returned HTTP {response.status_code}"
        except httpx.HTTPError:
            return "degraded", "Local OSRM is unavailable"
