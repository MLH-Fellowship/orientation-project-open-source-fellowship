"""add token usage columns to messages

Revision ID: 5a294dbc5fcf
Revises: cfa951b30af7
Create Date: 2026-09-22 16:21:44.118402

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5a294dbc5fcf"
down_revision: str | None = "cfa951b30af7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable: existing rows, user messages and streamed replies have no
    # usage to record.
    op.add_column("messages", sa.Column("prompt_tokens", sa.Integer(), nullable=True))
    op.add_column(
        "messages", sa.Column("completion_tokens", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("messages", "completion_tokens")
    op.drop_column("messages", "prompt_tokens")
