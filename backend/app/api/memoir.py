import io

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_storyteller
from app.db.session import get_db
from app.models.user import User
from app.schemas.memoir import MemoirContentUpdate, MemoirRead
from app.services import memoir_service, storage_service
from app.services.exceptions import (
    MemoirNotFoundError,
    NoDraftYetError,
    NoUsableAnswersError,
)

router = APIRouter()

MAX_PHOTO_UPLOAD_BYTES = 10 * 1024 * 1024


@router.post("/generate", response_model=MemoirRead)
async def generate_memoir(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_storyteller),
    db: AsyncSession = Depends(get_db),
):
    try:
        memoir, should_schedule = await memoir_service.trigger_draft_generation(
            db, current_user.account_id
        )
    except NoUsableAnswersError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Answer at least one question before generating a memoir.",
        )

    if should_schedule:
        background_tasks.add_task(
            memoir_service.generate_draft, memoir.id, current_user.account_id
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


@router.put("", response_model=MemoirRead)
async def update_memoir_content(
    data: MemoirContentUpdate,
    current_user: User = Depends(require_storyteller),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await memoir_service.update_content(
            db, current_user.account_id, data.content
        )
    except MemoirNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except NoDraftYetError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Generate a draft before editing it.",
        )


@router.put("/photo", response_model=MemoirRead)
async def upload_cover_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(require_storyteller),
    db: AsyncSession = Depends(get_db),
):
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    content = await file.read()
    if len(content) > MAX_PHOTO_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    try:
        Image.open(io.BytesIO(content)).verify()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="That file isn't a valid image.",
        )

    extension = storage_service.extension_from_content_type(content_type)
    try:
        return await memoir_service.upload_cover_photo(
            db, current_user.account_id, content, content_type, extension
        )
    except MemoirNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.delete("/photo", response_model=MemoirRead)
async def delete_cover_photo(
    current_user: User = Depends(require_storyteller),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await memoir_service.delete_cover_photo(db, current_user.account_id)
    except MemoirNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("/photo")
async def get_cover_photo(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        memoir = await memoir_service.get_cover_photo(db, current_user.account_id)
    except MemoirNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    content = await storage_service.read_media(memoir.cover_photo_path)
    return Response(content=content, media_type=memoir.cover_photo_content_type)


@router.post("/render", response_model=MemoirRead)
async def render_memoir_pdf(
    current_user: User = Depends(require_storyteller),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await memoir_service.render_pdf(db, current_user.account_id)
    except MemoirNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except NoDraftYetError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Generate a draft before creating the PDF.",
        )


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
