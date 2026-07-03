from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnswerUpsert(BaseModel):
    text: str


class AnswerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    text: str
    created_at: datetime
    updated_at: datetime
