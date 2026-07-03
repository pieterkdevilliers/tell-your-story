from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import verify_password
from app.models.user import User
from app.services.exceptions import (
    AccountNotAccessibleError,
    AmbiguousAccountError,
    InvalidCredentialsError,
)


async def authenticate_user(
    db: AsyncSession, email: str, password: str, account_id: Optional[int] = None
) -> User:
    stmt = select(User).where(User.email == email)
    if account_id is not None:
        stmt = stmt.where(User.account_id == account_id)

    candidates = (await db.execute(stmt)).scalars().all()
    matched = [u for u in candidates if verify_password(password, u.hashed_password)]

    if not matched:
        raise InvalidCredentialsError()
    if len(matched) > 1:
        raise AmbiguousAccountError(matched)
    return matched[0]


async def list_accounts_for_email(db: AsyncSession, email: str) -> list[User]:
    stmt = select(User).where(User.email == email).options(selectinload(User.account))
    return list((await db.execute(stmt)).scalars().all())


async def switch_account(db: AsyncSession, email: str, account_id: int) -> User:
    stmt = select(User).where(User.email == email, User.account_id == account_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise AccountNotAccessibleError()
    return user
