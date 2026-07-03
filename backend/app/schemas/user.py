from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import AccountRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: AccountRole = AccountRole.MEMBER


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[AccountRole] = None
    is_active: Optional[bool] = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: AccountRole
    is_active: bool
    account_id: int
    created_at: datetime
