from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_owner_or_storyteller
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.account import Account
from app.models.user import User
from app.schemas.auth import SignupResponse
from app.schemas.invite import InviteAccept, InviteCreate, InvitePreview, InviteRead
from app.services import invite_service
from app.services.exceptions import (
    EmailAlreadyExistsError,
    InvalidInviteTokenError,
    NoStorytellerYetError,
    StoryRequesterNotAllowedError,
    StorytellerAlreadyExistsError,
    UserTypeNotAllowedError,
)

router = APIRouter()


@router.post("", response_model=InviteRead, status_code=status.HTTP_201_CREATED)
async def create_invite(
    data: InviteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await invite_service.create_invite(
            db, current_user.account_id, current_user, data.email, data.user_type
        )
    except StoryRequesterNotAllowedError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="story_requester cannot be invited",
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
            detail="Add a storyteller before inviting viewers",
        )
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That email is already a member of this account",
        )


@router.get("", response_model=list[InviteRead])
async def list_invites(
    current_user: User = Depends(require_owner_or_storyteller),
    db: AsyncSession = Depends(get_db),
):
    return await invite_service.list_invites(db, current_user.account_id)


@router.get("/{token}", response_model=InvitePreview)
async def preview_invite(token: str, db: AsyncSession = Depends(get_db)):
    try:
        invite = await invite_service.get_invite_by_token(db, token)
    except InvalidInviteTokenError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invite",
        )
    account = await db.get(Account, invite.account_id)
    return InvitePreview(
        account_name=account.name,
        email=invite.email,
        user_type=invite.invited_user_type,
    )


@router.post("/accept", response_model=SignupResponse)
async def accept_invite(data: InviteAccept, db: AsyncSession = Depends(get_db)):
    try:
        user = await invite_service.accept_invite(db, data.token, data.password)
    except InvalidInviteTokenError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invite",
        )
    except StorytellerAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This account already has a storyteller",
        )
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You're already a member of this account",
        )

    await db.refresh(user, attribute_names=["account"])
    token = create_access_token(user.id, user.account_id, user.role.value)
    return SignupResponse(account=user.account, user=user, access_token=token)
