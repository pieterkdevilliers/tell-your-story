import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.account import Account


class AccountRole(str, enum.Enum):
    OWNER = "owner"
    MEMBER = "member"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("account_id", "email", name="uq_user_account_email"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(index=True)
    hashed_password: Mapped[str]
    role: Mapped[AccountRole]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    account: Mapped["Account"] = relationship(back_populates="users")
