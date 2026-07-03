from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.default_questions import DEFAULT_QUESTIONS
from app.models.question import Question
from app.services.exceptions import QuestionNotFoundError


async def list_questions(db: AsyncSession, account_id: int) -> list[Question]:
    stmt = (
        select(Question).where(Question.account_id == account_id).order_by(Question.id)
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_question(db: AsyncSession, account_id: int, text: str) -> Question:
    question = Question(account_id=account_id, text=text)
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return question


async def delete_question(db: AsyncSession, account_id: int, question_id: int) -> None:
    stmt = select(Question).where(
        Question.id == question_id, Question.account_id == account_id
    )
    question = (await db.execute(stmt)).scalar_one_or_none()
    if question is None:
        raise QuestionNotFoundError()

    await db.delete(question)
    await db.commit()


async def seed_default_questions(db: AsyncSession, account_id: int) -> None:
    for text in DEFAULT_QUESTIONS:
        db.add(Question(account_id=account_id, text=text))
