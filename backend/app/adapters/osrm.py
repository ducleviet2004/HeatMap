"""Client dùng để gọi OSRM Routing và Map Matching API."""

from typing import Any

import httpx


class OsrmClient:
    """Giao tiếp với OSRM self-hosted qua HTTP."""

    def __init__(self, base_url: str | None) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None

    async def status(self) -> tuple[str, str | None]:
        """Kiểm tra OSRM có sẵn sàng hay không."""
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

    async def get_route(
        self,
        coordinates: list[tuple[float, float]],
        overview: str = "full",
        geometries: str = "geojson",
    ) -> dict[str, Any] | None:
        """Lấy tuyến đường giữa các tọa độ."""
        if not self.base_url or len(coordinates) < 2:
            return None

        coord_str = ";".join(f"{lon},{lat}" for lon, lat in coordinates)
        url = f"{self.base_url}/route/v1/driving/{coord_str}"
        params = {
            "overview": overview,
            "geometries": geometries,
            "annotations": "nodes,distance,duration",
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, params=params)
            if response.status_code == 200:
                return response.json()  # type: ignore[no-any-return]
            return None
        except httpx.HTTPError:
            return None

    async def match_trace(
        self,
        coordinates: list[tuple[float, float]],
        timestamps: list[int] | None = None,
        radiuses: list[float] | None = None,
        overview: str = "full",
        geometries: str = "geojson",
    ) -> dict[str, Any] | None:
        """Gửi offline GPS trace tới OSRM Match API."""
        if not self.base_url or len(coordinates) < 2:
            return None

        coord_str = ";".join(f"{lon},{lat}" for lon, lat in coordinates)
        url = f"{self.base_url}/match/v1/driving/{coord_str}"
        params: dict[str, Any] = {
            "overview": overview,
            "geometries": geometries,
            "annotations": "nodes,distance,duration",
            "gaps": "split",
        }

        # Mỗi timestamp và radius phải ứng với đúng một coordinate.
        if timestamps and len(timestamps) == len(coordinates):
            params["timestamps"] = ";".join(str(t) for t in timestamps)
        if radiuses and len(radiuses) == len(coordinates):
            params["radiuses"] = ";".join(str(r) for r in radiuses)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, params=params)
            # NoMatch cũng trả HTTP 400; giữ JSON để service đọc được lý do cụ thể.
            if response.status_code in {200, 400}:
                return response.json()  # type: ignore[no-any-return]
            return None
        except httpx.HTTPError:
            return None
