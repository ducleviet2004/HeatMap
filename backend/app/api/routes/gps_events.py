from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi import status as http_status

from app.api.dependencies import get_gps_ingestion_service
from app.schemas.gps import GpsEventCreate
from app.services.gps_ingestion import GpsIngestionService

router = APIRouter(prefix="/gps", tags=["gps"])


@router.post("/events", status_code=http_status.HTTP_200_OK)
async def ingest_gps_event(
    data: GpsEventCreate,
    request: Request,
    service: Annotated[GpsIngestionService, Depends(get_gps_ingestion_service)],
) -> dict[str, object]:
    correlation_id = request.state.correlation_id
    await service.ingest(data, correlation_id=correlation_id)
    return {"accepted": True, "event_id": str(data.event_id)}
