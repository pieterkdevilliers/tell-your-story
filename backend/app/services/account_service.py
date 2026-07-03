from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.account import Account
from app.models.user import AccountRole, User


async def create_account_with_owner(
    db: AsyncSession, account_name: str, email: str, password: str
) -> tuple[Account, User]:
    account = Account(name=account_name)
    db.add(account)
    await db.flush()

    owner = User(
        account_id=account.id,
        email=email,
        hashed_password=hash_password(password),
        role=AccountRole.OWNER,
    )
    db.add(owner)

    await db.commit()
    await db.refresh(account)
    await db.refresh(owner)
    return account, owner
