from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_owner
from app.db.session import get_db
from app.models.user import AccountRole, User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import user_service
from app.services.exceptions import (
    EmailAlreadyExistsError,
    LastOwnerError,
    NoStorytellerYetError,
    StoryRequesterNotAllowedError,
    StorytellerAlreadyExistsError,
    UserNotFoundError,
    UserTypeNotAllowedError,
)

router = APIRouter()


@router.get("", response_model=list[UserRead])
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await user_service.list_users(db, current_user.account_id)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await user_service.get_user(db, current_user.account_id, user_id)
    except UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    current_user: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await user_service.create_user(
            db, current_user.account_id, current_user, data
        )
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    except StoryRequesterNotAllowedError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="story_requester cannot be created here",
        )
    except UserTypeNotAllowedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    except StorytellerAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This account already has a storyteller",
        )
    except NoStorytellerYetError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Add a storyteller before adding viewers",
        )


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_self = user_id == current_user.id
    is_owner = current_user.role == AccountRole.OWNER

    if not is_self and not is_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    if data.role is not None and not is_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    if data.is_active is not None and not is_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    if data.user_type is not None and not is_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:
        return await user_service.update_user(
            db, current_user.account_id, current_user, user_id, data
        )
    except UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    except StoryRequesterNotAllowedError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="story_requester cannot be set here",
        )
    except UserTypeNotAllowedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    except StorytellerAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This account already has a storyteller",
        )
    except NoStorytellerYetError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Add a storyteller before adding viewers",
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    try:
        await user_service.delete_user(db, current_user.account_id, user_id)
    except UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except LastOwnerError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
