from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.answer import Answer
from app.models.question import Question
from app.services.exceptions import QuestionNotFoundError


async def get_answers_by_question_ids(
    db: AsyncSession, question_ids: list[int]
) -> dict[int, Answer]:
    if not question_ids:
        return {}
    stmt = select(Answer).where(Answer.question_id.in_(question_ids))
    answers = (await db.execute(stmt)).scalars().all()
    return {answer.question_id: answer for answer in answers}


async def upsert_answer(
    db: AsyncSession, account_id: int, question_id: int, text: str
) -> Answer:
    question = await db.get(Question, question_id)
    if question is None or question.account_id != account_id:
        raise QuestionNotFoundError()

    stmt = select(Answer).where(Answer.question_id == question_id)
    answer = (await db.execute(stmt)).scalar_one_or_none()

    if answer is None:
        answer = Answer(question_id=question_id, account_id=account_id, text=text)
        db.add(answer)
    else:
        answer.text = text

    await db.commit()
    await db.refresh(answer)
    return answer
