"""Dịch vụ mã hóa không gian H3 Spatial Grid và thực thi Deduplication rule cho Heatmap."""

import math

import h3  # type: ignore[import-untyped]

MIN_H3_RESOLUTION = 9
MAX_H3_RESOLUTION = 12


class H3IndexingService:
    """Chuyển đổi đối tượng GeoJSON (Point, LineString) thành tập hợp ô H3."""

    @staticmethod
    def validate_resolution(resolution: int) -> None:
        """Kiểm tra độ phân giải H3 tuân thủ Rule 3 trong AGENTS.md (Resolution 9 đến 12)."""
        if not (MIN_H3_RESOLUTION <= resolution <= MAX_H3_RESOLUTION):
            raise ValueError(
                f"H3 resolution must be between {MIN_H3_RESOLUTION} and {MAX_H3_RESOLUTION}, "
                f"got {resolution}"
            )

    @classmethod
    def latlng_to_hex(cls, lat: float, lng: float, resolution: int = 9) -> str:
        """Chuyển đổi cặp tọa độ (latitude, longitude) thành H3 cell ID."""
        cls.validate_resolution(resolution)
        return str(h3.latlng_to_cell(lat, lng, resolution))

    @classmethod
    def linestring_to_hexes(
        cls,
        coordinates: list[list[float]],
        resolution: int = 9,
        sample_step_m: float = 20.0,
    ) -> set[str]:
        """Chuyển đổi chuỗi tọa độ GeoJSON [[lng, lat], ...] thành tập hợp unique set[str] các ô H3.

        Bảo đảm Deduplication rule: Mỗi trip chỉ thu về một tập hợp unique H3 hex IDs,
        loại bỏ hoàn toàn trùng lặp kể cả khi chuyến xe đi lặp lại nhiều lần trên cùng 1 ô H3.
        """
        cls.validate_resolution(resolution)
        if not coordinates:
            return set()

        hexes: set[str] = set()

        # Nội suy và lấy mẫu điểm dọc theo đoạn thẳng để không bỏ sót H3 cells ở giữa
        for i in range(len(coordinates) - 1):
            p1_lng, p1_lat = coordinates[i][0], coordinates[i][1]
            p2_lng, p2_lat = coordinates[i + 1][0], coordinates[i + 1][1]

            distance_m = cls._haversine_distance_m(p1_lat, p1_lng, p2_lat, p2_lng)
            steps = max(1, int(math.ceil(distance_m / sample_step_m)))

            for step in range(steps + 1):
                fraction = step / steps
                lat = p1_lat + (p2_lat - p1_lat) * fraction
                lng = p1_lng + (p2_lng - p1_lng) * fraction
                cell_id = h3.latlng_to_cell(lat, lng, resolution)
                hexes.add(str(cell_id))

        return hexes

    @staticmethod
    def _haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Tính khoảng cách haversine giữa 2 điểm (mét)."""
        r = 6371000.0  # Bán kính Trái Đất (m)
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = (
            math.sin(dphi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
        )
        return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
