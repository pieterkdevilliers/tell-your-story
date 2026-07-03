from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.question import QuestionCategory
from app.schemas.answer import AnswerRead


class QuestionCreate(BaseModel):
    category: QuestionCategory
    text: str


class QuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: QuestionCategory
    text: str
    account_id: int
    created_at: datetime
    answer: Optional[AnswerRead] = None
