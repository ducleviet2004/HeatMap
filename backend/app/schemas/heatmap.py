from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class HeatmapFeatureProperties(BaseModel):
    heat_weight: float = 0.0
    display_weight: float = 0.0


class HeatmapFeaturePropertiesWithMetrics(HeatmapFeatureProperties):
    hex_id: str | None = None
    h3_resolution: int | None = Field(default=None, ge=9, le=12)
    bypass_trip_count: int = 0
    eligible_trip_count: int = 0
    unique_driver_count: int = 0
    average_deviation_distance_m: float = 0.0


class HeatmapFeature(BaseModel):
    type: str = "Feature"
    properties: HeatmapFeatureProperties = HeatmapFeatureProperties()
    geometry: dict[str, object] = {"type": "Polygon", "coordinates": []}


class HeatmapFeatureWithMetrics(BaseModel):
    type: str = "Feature"
    properties: HeatmapFeaturePropertiesWithMetrics = Field(
        default_factory=HeatmapFeaturePropertiesWithMetrics
    )
    geometry: dict[str, object] = {"type": "Polygon", "coordinates": []}


class HeatmapResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[HeatmapFeature] = []


class HeatmapQueryParams(BaseModel):
    start_time: datetime | None = None
    end_time: datetime | None = None
    driver_id: UUID | None = None
    h3_resolution: int = Field(default=9, ge=9, le=12)


class HeatmapFilteredResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[HeatmapFeatureWithMetrics] = []
    query_params: HeatmapQueryParams | None = None
    total_bypass_trips: int = 0
    total_eligible_trips: int = 0
