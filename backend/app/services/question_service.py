from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.default_questions import DEFAULT_QUESTIONS
from app.models.question import Question, QuestionCategory
from app.services import answer_service
from app.services.exceptions import QuestionNotFoundError


async def list_questions(db: AsyncSession, account_id: int) -> list[Question]:
    stmt = (
        select(Question).where(Question.account_id == account_id).order_by(Question.id)
    )
    questions = list((await db.execute(stmt)).scalars().all())

    answers_by_question_id = await answer_service.get_answers_by_question_ids(
        db, [q.id for q in questions]
    )
    for question in questions:
        question.answer = answers_by_question_id.get(question.id)

    return questions


async def create_question(
    db: AsyncSession, account_id: int, category: QuestionCategory, text: str
) -> Question:
    question = Question(account_id=account_id, category=category, text=text)
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return question


async def update_question(
    db: AsyncSession, account_id: int, question_id: int, text: str
) -> Question:
    stmt = select(Question).where(
        Question.id == question_id, Question.account_id == account_id
    )
    question = (await db.execute(stmt)).scalar_one_or_none()
    if question is None:
        raise QuestionNotFoundError()

    question.text = text
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
    for category, texts in DEFAULT_QUESTIONS.items():
        for text in texts:
            db.add(Question(account_id=account_id, category=category, text=text))
