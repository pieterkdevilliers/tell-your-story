from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.user import User
from app.services.exceptions import AmbiguousAccountError, InvalidCredentialsError


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
