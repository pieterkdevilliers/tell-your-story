from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_owner
from app.db.session import get_db
from app.models.user import User
from app.schemas.question import QuestionCreate, QuestionRead
from app.services import question_service
from app.services.exceptions import QuestionNotFoundError

router = APIRouter()


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
