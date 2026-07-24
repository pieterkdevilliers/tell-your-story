from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.account import Account
from app.models.user import AccountRole, User, UserType
from app.services import email_templates, question_service
from app.services.email_service import send_email


async def create_account_with_owner(
    db: AsyncSession,
    account_name: str,
    email: str,
    password: str,
    user_type: UserType,
) -> tuple[Account, User]:
    account = Account(name=account_name)
    db.add(account)
    await db.flush()

    owner = User(
        account_id=account.id,
        email=email,
        hashed_password=hash_password(password),
        role=AccountRole.OWNER,
        user_type=user_type,
    )
    db.add(owner)
    await question_service.seed_default_questions(db, account.id)

    await db.commit()
    await db.refresh(account)
    await db.refresh(owner)

    template = (
        email_templates.signup_confirmation_storyteller
        if user_type == UserType.STORYTELLER
        else email_templates.signup_confirmation_story_requester
    )
    subject, html_body, text_body = template(account.name)
    await send_email(email, subject, text_body, html_body=html_body)

    return account, owner
