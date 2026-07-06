from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.default_questions import DEFAULT_QUESTIONS
from app.db.session import AsyncSessionLocal
from app.models.account import Account
from app.models.answer import AnswerType, TranscriptionStatus
from app.models.memoir import Memoir, MemoirStatus
from app.services import llm_service, pdf_service, question_service, storage_service
from app.services.exceptions import (
    MemoirNotFoundError,
    NoDraftYetError,
    NoUsableAnswersError,
)

CATEGORY_ORDER = list(DEFAULT_QUESTIONS.keys())


async def _collect_usable_entries(
    db: AsyncSession, account_id: int
) -> list[tuple[str, str, str]]:
    """Returns (chapter_label, question_text, answer_text) entries for
    every question with genuinely usable content — a non-empty text
    answer, or a non-empty transcript from a *completed* transcription.
    Anything else (no answer, an in-flight/failed transcription, an empty
    transcript) is silently omitted, so nothing unverified ever reaches
    the memoir prompt. Ordered by the same chapter sequence used to seed
    default questions, matching the frontend's category order.
    """
    questions = await question_service.list_questions(db, account_id)

    entries: list[tuple[str, str, str]] = []
    for question in questions:
        answer = question.answer
        if answer is None:
            continue
        if answer.answer_type == AnswerType.TEXT:
            if answer.text and answer.text.strip():
                entries.append((question.category, question.text, answer.text.strip()))
        elif (
            answer.transcription_status == TranscriptionStatus.COMPLETED
            and answer.transcript
            and answer.transcript.strip()
        ):
            entries.append(
                (question.category, question.text, answer.transcript.strip())
            )

    entries.sort(key=lambda entry: CATEGORY_ORDER.index(entry[0]))
    return entries


async def trigger_draft_generation(
    db: AsyncSession, account_id: int
) -> tuple[Memoir, bool]:
    """Returns (memoir, should_schedule) — should_schedule is False when an
    existing generation is already pending/processing, so the caller
    doesn't schedule a second background job for the same memoir.
    """
    entries = await _collect_usable_entries(db, account_id)
    if not entries:
        raise NoUsableAnswersError()

    stmt = select(Memoir).where(Memoir.account_id == account_id)
    memoir = (await db.execute(stmt)).scalar_one_or_none()

    if memoir is not None and memoir.status in (
        MemoirStatus.PENDING,
        MemoirStatus.PROCESSING,
    ):
        return memoir, False

    if memoir is None:
        memoir = Memoir(account_id=account_id, status=MemoirStatus.PENDING)
        db.add(memoir)
    else:
        # A fresh draft starts clean — any previous text/PDF no longer
        # applies. The cover photo isn't tied to a specific draft, so it's
        # left alone.
        memoir.status = MemoirStatus.PENDING
        memoir.content = None
        memoir.pdf_path = None

    await db.commit()
    await db.refresh(memoir)
    return memoir, True


async def generate_draft_with_session(
    db: AsyncSession, memoir_id: int, account_id: int
) -> None:
    """Runs draft text generation for one account and writes the result.

    Takes an explicit session (unlike `generate_draft` below) so it can
    be exercised directly against a test database — same split as
    answer_service.transcribe_answer / run_transcription.
    """
    memoir = await db.get(Memoir, memoir_id)
    if memoir is None or memoir.account_id != account_id:
        return

    memoir.status = MemoirStatus.PROCESSING
    await db.commit()

    try:
        entries = await _collect_usable_entries(db, account_id)
        account = await db.get(Account, account_id)
        memoir_text = await llm_service.generate_memoir_text(account.name, entries)
    except Exception:
        memoir.status = MemoirStatus.FAILED
        await db.commit()
        return

    memoir.content = memoir_text
    memoir.status = MemoirStatus.DRAFT_READY
    await db.commit()


async def generate_draft(memoir_id: int, account_id: int) -> None:
    """Background-task entrypoint invoked after draft generation is triggered."""
    async with AsyncSessionLocal() as db:
        await generate_draft_with_session(db, memoir_id, account_id)


async def get_memoir(db: AsyncSession, account_id: int) -> Memoir:
    stmt = select(Memoir).where(Memoir.account_id == account_id)
    memoir = (await db.execute(stmt)).scalar_one_or_none()
    if memoir is None:
        raise MemoirNotFoundError()
    return memoir


async def update_content(db: AsyncSession, account_id: int, text: str) -> Memoir:
    memoir = await get_memoir(db, account_id)
    if not memoir.content:
        raise NoDraftYetError()

    memoir.content = text
    # Reachable only from DRAFT_READY or COMPLETED (both imply content
    # already exists), so unconditionally resetting here is always
    # correct — editing a finalized memoir invalidates its PDF.
    memoir.pdf_path = None
    memoir.status = MemoirStatus.DRAFT_READY
    await db.commit()
    await db.refresh(memoir)
    return memoir


async def upload_cover_photo(
    db: AsyncSession, account_id: int, content: bytes, content_type: str, extension: str
) -> Memoir:
    memoir = await get_memoir(db, account_id)
    if memoir.cover_photo_path:
        await storage_service.delete_media(memoir.cover_photo_path)

    memoir.cover_photo_path = await storage_service.save_cover_photo(
        account_id, content, extension
    )
    memoir.cover_photo_content_type = content_type
    if memoir.status == MemoirStatus.COMPLETED:
        memoir.pdf_path = None
        memoir.status = MemoirStatus.DRAFT_READY

    await db.commit()
    await db.refresh(memoir)
    return memoir


async def delete_cover_photo(db: AsyncSession, account_id: int) -> Memoir:
    memoir = await get_memoir(db, account_id)
    if memoir.cover_photo_path:
        await storage_service.delete_media(memoir.cover_photo_path)
        memoir.cover_photo_path = None
        memoir.cover_photo_content_type = None
        if memoir.status == MemoirStatus.COMPLETED:
            memoir.pdf_path = None
            memoir.status = MemoirStatus.DRAFT_READY
        await db.commit()
        await db.refresh(memoir)
    return memoir


async def get_cover_photo(db: AsyncSession, account_id: int) -> Memoir:
    memoir = await get_memoir(db, account_id)
    if not memoir.cover_photo_path:
        raise MemoirNotFoundError()
    return memoir


async def render_pdf(db: AsyncSession, account_id: int) -> Memoir:
    memoir = await get_memoir(db, account_id)
    if not memoir.content:
        raise NoDraftYetError()

    cover_photo_bytes = None
    if memoir.cover_photo_path:
        cover_photo_bytes = await storage_service.read_media(memoir.cover_photo_path)

    pdf_bytes = await run_in_threadpool(
        pdf_service.render_memoir_pdf, memoir.content, cover_photo_bytes
    )
    memoir.pdf_path = await storage_service.save_pdf(account_id, pdf_bytes)
    memoir.status = MemoirStatus.COMPLETED
    await db.commit()
    await db.refresh(memoir)
    return memoir


async def get_memoir_pdf(db: AsyncSession, account_id: int) -> Memoir:
    memoir = await get_memoir(db, account_id)
    if not memoir.pdf_path:
        raise MemoirNotFoundError()
    return memoir
