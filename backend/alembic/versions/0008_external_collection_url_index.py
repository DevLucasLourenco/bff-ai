"""index external Fashion sources

Revision ID: 0008_external_collection_url_index
Revises: 0007_external_fashion_collection
"""

from alembic import op

revision = "0008_external_collection_url_index"
down_revision = "0007_external_fashion_collection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("wardrobe_items") as batch:
        batch.create_index("ix_wardrobe_items_owner_external_url", ["owner_id", "external_url"])


def downgrade() -> None:
    with op.batch_alter_table("wardrobe_items") as batch:
        batch.drop_index("ix_wardrobe_items_owner_external_url")
