from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_owner, require_storyteller
from app.db.session import get_db
from app.models.answer import AnswerType
from app.models.user import User
from app.schemas.answer import AnswerRead, AnswerUpsert
from app.schemas.question import QuestionCreate, QuestionRead
from app.services import answer_service, question_service, storage_service
from app.services.exceptions import QuestionNotFoundError

router = APIRouter()

MAX_MEDIA_UPLOAD_BYTES = 100 * 1024 * 1024


def _extension_from_content_type(content_type: str) -> str:
    base = content_type.split(";")[0].strip()
    return base.split("/")[-1] or "bin"


@router.get("", response_model=list[QuestionRead])
async def list_questions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await question_service.list_questions(db, current_user.account_id)


@router.post("", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
async def create_question(
    data: QuestionCreate,
    current_user: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    return await question_service.create_question(
        db, current_user.account_id, data.category, data.text
    )


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: int,
    current_user: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    try:
        await question_service.delete_question(db, current_user.account_id, question_id)
    except QuestionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.put("/{question_id}/answer", response_model=AnswerRead)
async def upsert_text_answer(
    question_id: int,
    data: AnswerUpsert,
    current_user: User = Depends(require_storyteller),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await answer_service.upsert_text_answer(
            db, current_user.account_id, question_id, data.text
        )
    except QuestionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.put("/{question_id}/answer/media", response_model=AnswerRead)
async def upsert_media_answer(
    question_id: int,
    answer_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_storyteller),
    db: AsyncSession = Depends(get_db),
):
    try:
        parsed_type = AnswerType(answer_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    if parsed_type == AnswerType.TEXT:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    content = await file.read()
    if len(content) > MAX_MEDIA_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    extension = _extension_from_content_type(file.content_type or "")
    try:
        return await answer_service.upsert_media_answer(
            db,
            current_user.account_id,
            question_id,
            parsed_type,
            content,
            file.content_type or "application/octet-stream",
            extension,
        )
    except QuestionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("/{question_id}/answer/media")
async def get_answer_media(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        answer = await answer_service.get_answer_media(
            db, current_user.account_id, question_id
        )
    except QuestionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    content = await storage_service.read_media(answer.media_path)
    return Response(content=content, media_type=answer.media_content_type)


@router.delete("/{question_id}/answer", status_code=status.HTTP_204_NO_CONTENT)
async def delete_answer(
    question_id: int,
    current_user: User = Depends(require_storyteller),
    db: AsyncSession = Depends(get_db),
):
    try:
        await answer_service.delete_answer(db, current_user.account_id, question_id)
    except QuestionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
