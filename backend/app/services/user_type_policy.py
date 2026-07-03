from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserType
from app.services.exceptions import (
    NoStorytellerYetError,
    StoryRequesterNotAllowedError,
    StorytellerAlreadyExistsError,
    UserTypeNotAllowedError,
)


async def _has_storyteller(
    db: AsyncSession, account_id: int, exclude_user_id: Optional[int] = None
) -> bool:
    stmt = select(User).where(
        User.account_id == account_id, User.user_type == UserType.STORYTELLER
    )
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def validate_user_type_assignment(
    db: AsyncSession,
    account_id: int,
    actor_user_type: UserType,
    target_user_type: UserType,
    *,
    exclude_user_id: Optional[int] = None,
) -> None:
    if target_user_type == UserType.STORY_REQUESTER:
        raise StoryRequesterNotAllowedError()

    if target_user_type == UserType.STORYTELLER:
        if actor_user_type != UserType.STORY_REQUESTER:
            raise UserTypeNotAllowedError()
        if await _has_storyteller(db, account_id, exclude_user_id):
            raise StorytellerAlreadyExistsError()
        return

    if actor_user_type not in (UserType.STORY_REQUESTER, UserType.STORYTELLER):
        raise UserTypeNotAllowedError()
    if not await _has_storyteller(db, account_id, exclude_user_id):
        raise NoStorytellerYetError()
