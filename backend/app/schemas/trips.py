from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TripCreate(BaseModel):
    external_id: str
    driver_id: UUID
    status: str = "planned"
    started_at: datetime


class TripResponse(BaseModel):
    id: UUID
    external_id: str
    driver_id: UUID
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
