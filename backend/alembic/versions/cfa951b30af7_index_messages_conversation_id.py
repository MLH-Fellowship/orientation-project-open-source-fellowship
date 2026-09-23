"""index messages.conversation_id

Revision ID: cfa951b30af7
Revises: f7ab3da63a2a
Create Date: 2026-09-22 15:42:11.237602

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cfa951b30af7"
down_revision: str | None = "f7ab3da63a2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        op.f("ix_messages_conversation_id"),
        "messages",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")
