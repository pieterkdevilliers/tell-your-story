from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QuestionCreate(BaseModel):
    text: str


class QuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    account_id: int
    created_at: datetime
