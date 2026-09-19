"""make an external source unique per owner

Revision ID: 0009_external_collection_url_unique
Revises: 0008_external_collection_url_index
"""

from alembic import op

revision = "0009_external_collection_url_unique"
down_revision = "0008_external_collection_url_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("wardrobe_items") as batch:
        batch.create_unique_constraint("uq_wardrobe_items_owner_external_url", ["owner_id", "external_url"])


def downgrade() -> None:
    with op.batch_alter_table("wardrobe_items") as batch:
        batch.drop_constraint("uq_wardrobe_items_owner_external_url", type_="unique")
