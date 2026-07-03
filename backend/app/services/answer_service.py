from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.answer import Answer, AnswerType
from app.models.question import Question
from app.services import storage_service
from app.services.exceptions import QuestionNotFoundError


async def get_answers_by_question_ids(
    db: AsyncSession, question_ids: list[int]
) -> dict[int, Answer]:
    if not question_ids:
        return {}
    stmt = select(Answer).where(Answer.question_id.in_(question_ids))
    answers = (await db.execute(stmt)).scalars().all()
    return {answer.question_id: answer for answer in answers}


async def _get_existing_answer(
    db: AsyncSession, account_id: int, question_id: int
) -> Optional[Answer]:
    """Validates the question belongs to this account, then returns its
    existing answer (if any). Shared by both the text and media upsert
    paths so the cross-account check lives in exactly one place."""
    question = await db.get(Question, question_id)
    if question is None or question.account_id != account_id:
        raise QuestionNotFoundError()

    stmt = select(Answer).where(Answer.question_id == question_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def upsert_text_answer(
    db: AsyncSession, account_id: int, question_id: int, text: str
) -> Answer:
    answer = await _get_existing_answer(db, account_id, question_id)

    if answer is not None and answer.media_path:
        await storage_service.delete_media(answer.media_path)

    if answer is None:
        answer = Answer(
            question_id=question_id,
            account_id=account_id,
            answer_type=AnswerType.TEXT,
            text=text,
        )
        db.add(answer)
    else:
        answer.answer_type = AnswerType.TEXT
        answer.text = text
        answer.media_path = None
        answer.media_content_type = None

    await db.commit()
    await db.refresh(answer)
    return answer


async def upsert_media_answer(
    db: AsyncSession,
    account_id: int,
    question_id: int,
    answer_type: AnswerType,
    content: bytes,
    content_type: str,
    extension: str,
) -> Answer:
    answer = await _get_existing_answer(db, account_id, question_id)

    if answer is not None and answer.media_path:
        await storage_service.delete_media(answer.media_path)

    storage_key = await storage_service.save_media(
        account_id, question_id, content, extension
    )

    if answer is None:
        answer = Answer(
            question_id=question_id,
            account_id=account_id,
            answer_type=answer_type,
            media_path=storage_key,
            media_content_type=content_type,
        )
        db.add(answer)
    else:
        answer.answer_type = answer_type
        answer.text = None
        answer.media_path = storage_key
        answer.media_content_type = content_type

    await db.commit()
    await db.refresh(answer)
    return answer


async def delete_answer(db: AsyncSession, account_id: int, question_id: int) -> None:
    stmt = select(Answer).where(
        Answer.question_id == question_id, Answer.account_id == account_id
    )
    answer = (await db.execute(stmt)).scalar_one_or_none()
    if answer is None:
        raise QuestionNotFoundError()

    if answer.media_path:
        await storage_service.delete_media(answer.media_path)

    await db.delete(answer)
    await db.commit()


async def get_answer_media(
    db: AsyncSession, account_id: int, question_id: int
) -> Answer:
    stmt = select(Answer).where(
        Answer.question_id == question_id, Answer.account_id == account_id
    )
    answer = (await db.execute(stmt)).scalar_one_or_none()
    if answer is None or not answer.media_path:
        raise QuestionNotFoundError()
    return answer
