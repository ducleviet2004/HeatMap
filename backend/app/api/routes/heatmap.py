import h3
from fastapi import APIRouter

from app.schemas.heatmap import (
    HeatmapFeature,
    HeatmapFeatureProperties,
    HeatmapResponse,
)

router = APIRouter(tags=["heatmap"])

# Hanoi sample H3 cells around Ring Road 3, Thang Long, Nhat Tan Bridge, Hoan Kiem
HANOI_SAMPLE_H3_DATA = [
    ("8941436967bffff", 48),
    ("89415cb4923ffff", 85),
    ("8941436b2c3ffff", 120),
    ("89415cb6bafffff", 32),
    ("89415cb6847ffff", 67),
    ("894143694cfffff", 94),
    ("8941436821bffff", 51),
    ("89414368e13ffff", 110),
    ("89415cb4e13ffff", 145),
    ("89415cb5967ffff", 76),
    ("89415ca71cbffff", 88),
    ("89415cb4e43ffff", 102),
    ("89415cb412bffff", 63),
    ("89415cb6a43ffff", 79),
]


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap() -> HeatmapResponse:
    features = []
    for hex_id, count in HANOI_SAMPLE_H3_DATA:
        # Convert H3 hex boundary to GeoJSON coordinates [lon, lat]
        boundary = h3.cell_to_boundary(hex_id)
        # GeoJSON expects [longitude, latitude]
        coords = [[lon, lat] for lat, lon in boundary]
        if coords:
            coords.append(coords[0])  # Close linear ring

        features.append(
            HeatmapFeature(
                type="Feature",
                properties=HeatmapFeatureProperties(
                    hex_id=hex_id,
                    h3_resolution=9,
                    bypass_trip_count=count,
                    heat_weight=float(count),
                    display_weight=float(count),
                ),
                geometry={"type": "Polygon", "coordinates": [coords]},
            )
        )

    return HeatmapResponse(type="FeatureCollection", features=features)
