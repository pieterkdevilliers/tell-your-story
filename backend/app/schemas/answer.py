from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.answer import AnswerType, TranscriptionStatus


class AnswerUpsert(BaseModel):
    text: str


class AnswerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    answer_type: AnswerType
    text: Optional[str] = None
    transcript: Optional[str] = None
    transcription_status: Optional[TranscriptionStatus] = None
    created_at: datetime
    updated_at: datetime
