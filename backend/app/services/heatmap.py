import h3.api.numpy_int as h3_api
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.h3_hexes import H3HexRepository
from app.schemas.heatmap import (
    HeatmapFeaturePropertiesWithMetrics,
    HeatmapFeatureWithMetrics,
    HeatmapFilteredResponse,
    HeatmapQueryParams,
)


class HeatmapService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = H3HexRepository(session)

    async def query_filtered(
        self,
        params: HeatmapQueryParams,
    ) -> HeatmapFilteredResponse:
        aggregates = await self.repo.get_heatmap_features(
            h3_resolution=params.h3_resolution,
            start_time=params.start_time,
            end_time=params.end_time,
        )

        total_bypass = 0
        total_eligible = 0
        features: list[HeatmapFeatureWithMetrics] = []

        for agg in aggregates:
            boundary = h3_api.cell_to_boundary(agg.hex_id)
            coordinates = [[boundary[j][1], boundary[j][0]] for j in range(len(boundary))]
            coordinates.append(coordinates[0])

            props = HeatmapFeaturePropertiesWithMetrics(
                heat_weight=agg.eligible_trip_count,
                display_weight=agg.bypass_trip_count,
                bypass_trip_count=agg.bypass_trip_count,
                eligible_trip_count=agg.eligible_trip_count,
                unique_driver_count=agg.unique_driver_count,
                average_deviation_distance_m=agg.average_deviation_distance_m,
            )
            features.append(
                HeatmapFeatureWithMetrics(
                    type="Feature",
                    properties=props,
                    geometry={"type": "Polygon", "coordinates": [coordinates]},
                )
            )
            total_bypass += agg.bypass_trip_count
            total_eligible += agg.eligible_trip_count

        return HeatmapFilteredResponse(
            type="FeatureCollection",
            features=features,
            query_params=params,
            total_bypass_trips=total_bypass,
            total_eligible_trips=total_eligible,
        )
