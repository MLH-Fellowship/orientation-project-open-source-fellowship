"""add title_is_default to conversations

Revision ID: f7a691d82820
Revises: 6ae937be5a31
Create Date: 2026-09-23 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7a691d82820"
down_revision: str | None = "6ae937be5a31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("title_is_default", sa.Boolean(), nullable=True),
    )
    conversations = sa.table(
        "conversations",
        sa.column("title", sa.String),
        sa.column("title_is_default", sa.Boolean),
    )
    # Backfill from the only signal we had before this column existed.
    op.execute(
        conversations.update().values(
            title_is_default=(conversations.c.title == "New Conversation")
        )
    )
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.alter_column("title_is_default", nullable=False)


def downgrade() -> None:
    op.drop_column("conversations", "title_is_default")
