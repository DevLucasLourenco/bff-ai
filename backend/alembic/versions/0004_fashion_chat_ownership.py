"""fashion chat ownership and tool capability

Revision ID: 0004_fashion_chat_ownership
Revises: 0003_fashion_module_core
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_fashion_chat_ownership"
down_revision = "0003_fashion_module_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("model_configs") as batch:
        batch.add_column(sa.Column("supports_tools", sa.Boolean(), server_default="0", nullable=False))

    # Existing local conversations belong to the bootstrap owner. A later auth
    # migration only needs to replace this deterministic backfill.
    with op.batch_alter_table("conversations") as batch:
        batch.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
    op.execute("UPDATE conversations SET owner_id = 1 WHERE owner_id IS NULL")
    with op.batch_alter_table("conversations") as batch:
        batch.alter_column("owner_id", nullable=False)
        batch.create_foreign_key("fk_conversations_owner_id_users", "users", ["owner_id"], ["id"], ondelete="CASCADE")
        batch.create_index("ix_conversations_owner_id", ["owner_id"])

    op.create_table(
        "outfit_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("outfit_id", sa.Integer(), nullable=False),
        sa.Column("liked", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["outfit_id"], ["outfits.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outfit_feedback_owner_id", "outfit_feedback", ["owner_id"])
    op.create_index("ix_outfit_feedback_outfit_id", "outfit_feedback", ["outfit_id"])


def downgrade() -> None:
    op.drop_table("outfit_feedback")
    with op.batch_alter_table("conversations") as batch:
        batch.drop_index("ix_conversations_owner_id")
        batch.drop_constraint("fk_conversations_owner_id_users", type_="foreignkey")
        batch.drop_column("owner_id")
    with op.batch_alter_table("model_configs") as batch:
        batch.drop_column("supports_tools")
