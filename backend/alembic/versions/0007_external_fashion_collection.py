"""add external Fashion collection provenance

Revision ID: 0007_external_fashion_collection
Revises: 0006_remove_global_fashion_setting
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_external_fashion_collection"
down_revision = "0006_remove_global_fashion_setting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("wardrobe_items") as batch:
        batch.add_column(sa.Column("collection_status", sa.String(length=20), nullable=False, server_default="owned"))
        batch.add_column(sa.Column("external_url", sa.String(length=2048), nullable=True))
        batch.add_column(sa.Column("external_domain", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("external_captured_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_wardrobe_items_owner_collection_status", ["owner_id", "collection_status"])


def downgrade() -> None:
    with op.batch_alter_table("wardrobe_items") as batch:
        batch.drop_index("ix_wardrobe_items_owner_collection_status")
        batch.drop_column("external_captured_at")
        batch.drop_column("external_domain")
        batch.drop_column("external_url")
        batch.drop_column("collection_status")
