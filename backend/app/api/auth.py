from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AccountChoice,
    LoginRequest,
    LoginResponse,
    MeResponse,
    SignupRequest,
    SignupResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.password_reset import PasswordResetConfirm, PasswordResetRequest
from app.services import account_service, auth_service, password_reset_service
from app.services.exceptions import (
    AmbiguousAccountError,
    InvalidCredentialsError,
    InvalidResetTokenError,
)

router = APIRouter()


@router.post("/signup", response_model=SignupResponse)
async def signup(data: SignupRequest, db: AsyncSession = Depends(get_db)):
    account, owner = await account_service.create_account_with_owner(
        db, data.account_name, data.email, data.password
    )
    token = create_access_token(owner.id, account.id, owner.role.value)
    return SignupResponse(account=account, user=owner, access_token=token)


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await auth_service.authenticate_user(
            db, data.email, data.password, data.account_id
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    except AmbiguousAccountError as exc:
        accounts = []
        for candidate in exc.candidates:
            await db.refresh(candidate, attribute_names=["account"])
            accounts.append(
                AccountChoice(id=candidate.account.id, name=candidate.account.name)
            )
        return LoginResponse(accounts=accounts)

    await db.refresh(user, attribute_names=["account"])
    token = create_access_token(user.id, user.account_id, user.role.value)
    return LoginResponse(
        access_token=token, token_type="bearer", user=user, account=user.account
    )


@router.get("/me", response_model=MeResponse)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.refresh(current_user, attribute_names=["account"])
    return MeResponse(user=current_user, account=current_user.account)


@router.post("/password-reset/request", response_model=MessageResponse)
async def request_password_reset(
    data: PasswordResetRequest, db: AsyncSession = Depends(get_db)
):
    await password_reset_service.request_password_reset(db, data.email)
    return MessageResponse(
        message="If that email exists, we've sent password reset instructions."
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    data: PasswordResetConfirm, db: AsyncSession = Depends(get_db)
):
    try:
        await password_reset_service.confirm_password_reset(
            db, data.token, data.new_password
        )
    except InvalidResetTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    return MessageResponse(message="Your password has been reset. Please log in.")
