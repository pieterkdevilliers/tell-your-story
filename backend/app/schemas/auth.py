from typing import Optional

from pydantic import BaseModel, EmailStr

from app.schemas.account import AccountRead
from app.schemas.user import UserRead


class SignupRequest(BaseModel):
    account_name: str
    email: EmailStr
    password: str


class SignupResponse(BaseModel):
    account: AccountRead
    user: UserRead
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    account_id: Optional[int] = None


class AccountChoice(BaseModel):
    id: int
    name: str


class LoginResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    user: Optional[UserRead] = None
    account: Optional[AccountRead] = None
    accounts: Optional[list[AccountChoice]] = None


class MeResponse(BaseModel):
    user: UserRead
    account: AccountRead
