from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.memoir import MemoirStatus


class MemoirRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: MemoirStatus
    content: Optional[str] = None
    has_cover_photo: bool
    created_at: datetime
    updated_at: datetime


class MemoirContentUpdate(BaseModel):
    content: str
