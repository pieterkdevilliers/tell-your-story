import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import AccountRole, User
from app.services.exceptions import UserNotFoundError
from app.services.user_service import get_user

security = HTTPBearer()


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = decode_access_token(creds.credentials)
        user_id = int(payload["sub"])
        account_id = int(payload["account_id"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized

    try:
        return await get_user(db, account_id, user_id)
    except UserNotFoundError:
        raise unauthorized


def require_owner(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != AccountRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the account owner can perform this action",
        )
    return current_user
