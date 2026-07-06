from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_storyteller
from app.db.session import get_db
from app.models.user import User
from app.schemas.memoir import MemoirRead
from app.services import memoir_service, storage_service
from app.services.exceptions import MemoirNotFoundError, NoUsableAnswersError

router = APIRouter()


@router.post("/generate", response_model=MemoirRead)
async def generate_memoir(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_storyteller),
    db: AsyncSession = Depends(get_db),
):
    try:
        memoir, should_schedule = await memoir_service.trigger_generation(
            db, current_user.account_id
        )
    except NoUsableAnswersError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Answer at least one question before generating a memoir.",
        )

    if should_schedule:
        background_tasks.add_task(
            memoir_service.generate, memoir.id, current_user.account_id
        )
    return memoir


@router.get("", response_model=MemoirRead)
async def get_memoir(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await memoir_service.get_memoir(db, current_user.account_id)
    except MemoirNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("/pdf")
async def get_memoir_pdf(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        memoir = await memoir_service.get_memoir_pdf(db, current_user.account_id)
    except MemoirNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    content = await storage_service.read_media(memoir.pdf_path)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="memoir.pdf"'},
    )
