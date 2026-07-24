from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status

from app.api.dependencies import get_trip_service
from app.schemas.trips import TripCreate, TripResponse
from app.services.trips import TripService

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("", response_model=TripResponse, status_code=http_status.HTTP_201_CREATED)
async def create_trip(
    data: TripCreate,
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripResponse:
    return await service.create_trip(data)


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: UUID,
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripResponse:
    trip = await service.get_trip(trip_id)
    if trip is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return trip


@router.post("/{trip_id}/complete", response_model=TripResponse)
async def complete_trip(
    trip_id: UUID,
    service: Annotated[TripService, Depends(get_trip_service)],
) -> TripResponse:
    trip = await service.finalize_trip(trip_id)
    if trip is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return trip
