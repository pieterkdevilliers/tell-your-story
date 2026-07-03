import enum
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QuestionCategory(str, enum.Enum):
    EARLY_LIFE_FAMILY = "early_life_family"
    CHILDHOOD_FAMILY_LIFE = "childhood_family_life"
    SCHOOL_GROWING_UP = "school_growing_up"
    CAREER_WORK = "career_work"
    LOVE_RELATIONSHIPS = "love_relationships"
    MAJOR_LIFE_EVENTS = "major_life_events"
    VALUES_BELIEFS_REFLECTIONS = "values_beliefs_reflections"
    ADVICE_LEGACY = "advice_legacy"


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[QuestionCategory]
    text: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
