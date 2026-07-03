from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import FRONTEND_URL, PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
from app.core.security import generate_reset_token, hash_password, hash_reset_token
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services.email_service import send_email
from app.services.exceptions import InvalidResetTokenError


async def request_password_reset(db: AsyncSession, email: str) -> None:
    stmt = select(User).where(User.email == email).options(selectinload(User.account))
    users = (await db.execute(stmt)).scalars().all()
    if not users:
        return

    raw_token = generate_reset_token()
    record = PasswordResetToken(
        email=email,
        token_hash=hash_reset_token(raw_token),
        expires_at=datetime.utcnow()
        + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
    )
    db.add(record)
    await db.commit()

    reset_link = f"{FRONTEND_URL}/reset-password?token={raw_token}"
    account_names = ", ".join(user.account.name for user in users)
    body = (
        "We received a request to reset your password.\n\n"
        f"This will reset your password for: {account_names}.\n\n"
        f"Reset your password: {reset_link}\n\n"
        f"This link expires in {PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes. "
        "If you didn't request this, you can safely ignore this email."
    )
    await send_email(email, "Reset your password", body)


async def confirm_password_reset(
    db: AsyncSession, token: str, new_password: str
) -> None:
    token_hash = hash_reset_token(token)
    stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    record = (await db.execute(stmt)).scalar_one_or_none()

    if (
        record is None
        or record.used_at is not None
        or record.expires_at < datetime.utcnow()
    ):
        raise InvalidResetTokenError()

    stmt = select(User).where(User.email == record.email)
    users = (await db.execute(stmt)).scalars().all()
    hashed = hash_password(new_password)
    for user in users:
        user.hashed_password = hashed

    record.used_at = datetime.utcnow()
    await db.commit()
