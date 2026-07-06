"""add memoir draft status and cover photo fields

Revision ID: 829b894c4318
Revises: a6976e0eab8a
Create Date: 2026-07-06 12:32:37.081408

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "829b894c4318"
down_revision: Union[str, Sequence[str], None] = "a6976e0eab8a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The status column's declared VARCHAR length is stale (SQLite doesn't
    # enforce it, and there's no other engine in play), so it's left alone
    # here — only the two new nullable columns are added.
    op.add_column("memoirs", sa.Column("cover_photo_path", sa.String(), nullable=True))
    op.add_column(
        "memoirs", sa.Column("cover_photo_content_type", sa.String(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("memoirs", "cover_photo_content_type")
    op.drop_column("memoirs", "cover_photo_path")
