from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DriverResponse(BaseModel):
    id: UUID
    external_id: str
    display_name: str
    status: str
    created_at: datetime
    updated_at: datetime
