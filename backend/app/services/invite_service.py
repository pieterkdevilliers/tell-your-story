from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import FRONTEND_URL, INVITE_TOKEN_EXPIRE_MINUTES
from app.core.security import generate_reset_token, hash_password, hash_reset_token
from app.models.account import Account
from app.models.invite import Invite
from app.models.user import AccountRole, User, UserType
from app.services import email_templates
from app.services.email_service import send_email
from app.services.exceptions import (
    EmailAlreadyExistsError,
    InvalidInviteTokenError,
    StorytellerAlreadyExistsError,
)
from app.services.user_type_policy import validate_user_type_assignment


async def create_invite(
    db: AsyncSession, account_id: int, inviter: User, email: str, user_type: UserType
) -> Invite:
    await validate_user_type_assignment(db, account_id, inviter.user_type, user_type)

    stmt = select(User).where(User.account_id == account_id, User.email == email)
    if (await db.execute(stmt)).scalar_one_or_none() is not None:
        raise EmailAlreadyExistsError()

    raw_token = generate_reset_token()
    invite = Invite(
        account_id=account_id,
        email=email,
        token_hash=hash_reset_token(raw_token),
        invited_user_type=user_type,
        invited_by_user_id=inviter.id,
        expires_at=datetime.utcnow() + timedelta(minutes=INVITE_TOKEN_EXPIRE_MINUTES),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    account = await db.get(Account, account_id)
    invite_link = f"{FRONTEND_URL}/invite/{raw_token}"
    template = (
        email_templates.invite_storyteller
        if user_type == UserType.STORYTELLER
        else email_templates.invite_viewer
    )
    subject, html_body, text_body = template(
        account.name, invite_link, INVITE_TOKEN_EXPIRE_MINUTES
    )
    await send_email(email, subject, text_body, html_body=html_body)
    return invite


async def get_invite_by_token(db: AsyncSession, token: str) -> Invite:
    token_hash = hash_reset_token(token)
    stmt = select(Invite).where(Invite.token_hash == token_hash)
    invite = (await db.execute(stmt)).scalar_one_or_none()
    if (
        invite is None
        or invite.accepted_at is not None
        or invite.expires_at < datetime.utcnow()
    ):
        raise InvalidInviteTokenError()
    return invite


async def accept_invite(db: AsyncSession, token: str, password: str) -> User:
    invite = await get_invite_by_token(db, token)

    if invite.invited_user_type == UserType.STORYTELLER:
        stmt = select(User).where(
            User.account_id == invite.account_id,
            User.user_type == UserType.STORYTELLER,
        )
        if (await db.execute(stmt)).scalar_one_or_none() is not None:
            raise StorytellerAlreadyExistsError()

    stmt = select(User).where(
        User.account_id == invite.account_id, User.email == invite.email
    )
    if (await db.execute(stmt)).scalar_one_or_none() is not None:
        raise EmailAlreadyExistsError()

    user = User(
        account_id=invite.account_id,
        email=invite.email,
        hashed_password=hash_password(password),
        role=AccountRole.MEMBER,
        user_type=invite.invited_user_type,
    )
    db.add(user)
    invite.accepted_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def list_invites(db: AsyncSession, account_id: int) -> list[Invite]:
    stmt = select(Invite).where(Invite.account_id == account_id)
    return list((await db.execute(stmt)).scalars().all())
