from pydantic import BaseModel


class HeatmapFeatureProperties(BaseModel):
    heat_weight: float = 0.0
    display_weight: float = 0.0


class HeatmapFeature(BaseModel):
    type: str = "Feature"
    properties: HeatmapFeatureProperties = HeatmapFeatureProperties()
    geometry: dict[str, object] = {"type": "Polygon", "coordinates": []}


class HeatmapResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[HeatmapFeature] = []
