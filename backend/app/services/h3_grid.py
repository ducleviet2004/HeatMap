"""Chuyen confirmed bypass LineString sang H3 resolution 9-12."""

from math import asin, cos, radians, sin, sqrt
from uuid import UUID

import h3

from app.schemas.h3_grid import BypassGeometry, H3ConversionResult, TripRouteHexRecord

EARTH_RADIUS_M = 6_371_008.8


class BypassH3Service:
    """Phu bypass bang H3 va chi tao mot record cho moi trip/hex/resolution."""

    def __init__(
        self,
        *,
        resolutions: tuple[int, ...] = (9, 10, 11, 12),
        algorithm_version: str = "bypass-h3-v1",
    ) -> None:
        if not resolutions or any(resolution < 9 or resolution > 12 for resolution in resolutions):
            raise ValueError("H3 resolutions must be between 9 and 12")
        self.resolutions = tuple(sorted(set(resolutions)))
        self.algorithm_version = algorithm_version

    def convert(
        self,
        *,
        trip_id: UUID,
        planned_route_id: UUID,
        bypass_segments: list[BypassGeometry],
    ) -> H3ConversionResult:
        """Convert confirmed segment va deduplicate truoc khi ghi database."""
        unique_cells: set[tuple[int, str]] = set()

        for segment in bypass_segments:
            if not segment.confirmed:
                continue
            for resolution in self.resolutions:
                for cell in self._line_cells(segment.coordinates, resolution):
                    unique_cells.add((resolution, cell))

        records = [
            TripRouteHexRecord(
                trip_id=trip_id,
                planned_route_id=planned_route_id,
                hex_id=cell,
                h3_resolution=resolution,
                algorithm_version=self.algorithm_version,
            )
            for resolution, cell in sorted(unique_cells)
        ]
        return H3ConversionResult(records=records)

    @classmethod
    def _line_cells(cls, coordinates: list[tuple[float, float]], resolution: int) -> set[str]:
        """Lay cell doc LineString; sample point cach nhau toi da nua canh H3."""
        spacing_m = h3.average_hexagon_edge_length(resolution, unit="m") / 2
        cells: set[str] = set()
        previous_cell: str | None = None

        for start, end in zip(coordinates, coordinates[1:], strict=False):
            distance_m = cls._distance_m(start, end)
            step_count = max(1, int(distance_m / spacing_m) + 1)
            for step in range(step_count + 1):
                ratio = step / step_count
                longitude = start[0] + ((end[0] - start[0]) * ratio)
                latitude = start[1] + ((end[1] - start[1]) * ratio)
                cell = h3.latlng_to_cell(latitude, longitude, resolution)
                cells.add(cell)

                # Noi hai sample cell de khong bo sot cell khi line cat qua H3 boundary.
                if previous_cell is not None and previous_cell != cell:
                    try:
                        cells.update(h3.grid_path_cells(previous_cell, cell))
                    except h3.H3FailedError:
                        # Van giu sample cell neu H3 khong tim duoc path gan pentagon.
                        pass
                previous_cell = cell
        return cells

    @staticmethod
    def _distance_m(start: tuple[float, float], end: tuple[float, float]) -> float:
        """Tinh Haversine distance vi input coordinate la WGS84 lon/lat."""
        lon1, lat1 = start
        lon2, lat2 = end
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)
        value = (
            sin(delta_lat / 2) ** 2
            + cos(radians(lat1)) * cos(radians(lat2)) * sin(delta_lon / 2) ** 2
        )
        return 2 * EARTH_RADIUS_M * asin(sqrt(value))
