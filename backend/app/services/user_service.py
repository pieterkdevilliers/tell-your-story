from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import AccountRole, User
from app.schemas.user import UserCreate, UserUpdate
from app.services.exceptions import (
    EmailAlreadyExistsError,
    LastOwnerError,
    UserNotFoundError,
)


async def list_users(db: AsyncSession, account_id: int) -> list[User]:
    stmt = select(User).where(User.account_id == account_id)
    return list((await db.execute(stmt)).scalars().all())


async def get_user(db: AsyncSession, account_id: int, user_id: int) -> User:
    stmt = select(User).where(User.id == user_id, User.account_id == account_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise UserNotFoundError()
    return user


async def _email_taken(db: AsyncSession, account_id: int, email: str) -> bool:
    stmt = select(User).where(User.account_id == account_id, User.email == email)
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def create_user(db: AsyncSession, account_id: int, data: UserCreate) -> User:
    if await _email_taken(db, account_id, data.email):
        raise EmailAlreadyExistsError()

    user = User(
        account_id=account_id,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(
    db: AsyncSession, account_id: int, user_id: int, data: UserUpdate
) -> User:
    user = await get_user(db, account_id, user_id)

    if data.email is not None and data.email != user.email:
        if await _email_taken(db, account_id, data.email):
            raise EmailAlreadyExistsError()
        user.email = data.email

    if data.password is not None:
        user.hashed_password = hash_password(data.password)
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active

    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, account_id: int, user_id: int) -> None:
    user = await get_user(db, account_id, user_id)

    if user.role == AccountRole.OWNER:
        stmt = select(func.count()).where(
            User.account_id == account_id,
            User.role == AccountRole.OWNER,
            User.id != user_id,
        )
        remaining_owners = (await db.execute(stmt)).scalar_one()
        if remaining_owners == 0:
            raise LastOwnerError()

    await db.delete(user)
    await db.commit()
