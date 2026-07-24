from fastapi import APIRouter

from app.schemas.heatmap import HeatmapResponse

router = APIRouter(tags=["heatmap"])


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap() -> HeatmapResponse:
    return HeatmapResponse()
