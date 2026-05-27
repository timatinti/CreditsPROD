from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class DraftCreate(BaseModel):
    user_id: str
    data: dict       # поля заявки
    step: int

class DraftResponse(BaseModel):
    id: UUID
    user_id: str
    data: dict
    step: int
    updated_at: datetime