from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.memoir import MemoirStatus


class MemoirRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: MemoirStatus
    created_at: datetime
    updated_at: datetime
