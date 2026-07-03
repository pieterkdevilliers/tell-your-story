from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserType


class InviteCreate(BaseModel):
    email: EmailStr
    user_type: UserType


class InviteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    invited_user_type: UserType
    account_id: int
    expires_at: datetime
    accepted_at: Optional[datetime]
    created_at: datetime


class InvitePreview(BaseModel):
    account_name: str
    email: str
    user_type: UserType


class InviteAccept(BaseModel):
    token: str
    password: str
