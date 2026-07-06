"""add transcript and transcription status to answers

Revision ID: 419bf11b851f
Revises: 8e73b217cdea
Create Date: 2026-07-06 10:51:27.538094

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "419bf11b851f"
down_revision: Union[str, Sequence[str], None] = "8e73b217cdea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Both columns are nullable, so unlike the answer_type/media_path
    # migration, plain add_column works on SQLite without batch mode.
    op.add_column("answers", sa.Column("transcript", sa.String(), nullable=True))
    op.add_column(
        "answers",
        sa.Column(
            "transcription_status",
            sa.Enum(
                "PENDING",
                "PROCESSING",
                "COMPLETED",
                "FAILED",
                name="transcriptionstatus",
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("answers", "transcription_status")
    op.drop_column("answers", "transcript")
