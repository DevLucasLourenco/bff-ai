"""chat Fashion image attachments

Revision ID: 0005_chat_fashion_attachments
Revises: 0004_fashion_chat_ownership
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_chat_fashion_attachments"
down_revision = "0004_fashion_chat_ownership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("messages") as batch:
        batch.add_column(sa.Column("attachment_asset_ids", sa.JSON(), server_default="[]", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("messages") as batch:
        batch.drop_column("attachment_asset_ids")
