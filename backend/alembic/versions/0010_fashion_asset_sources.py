"""keep provenance on chat assets imported from links

Revision ID: 0010_fashion_asset_sources
Revises: 0009_external_collection_url_unique
"""

from alembic import op
import sqlalchemy as sa

revision = "0010_fashion_asset_sources"
down_revision = "0009_external_collection_url_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("fashion_assets") as batch:
        batch.add_column(sa.Column("source_url", sa.String(length=2048), nullable=True))
        batch.add_column(sa.Column("source_image_url", sa.String(length=2048), nullable=True))
        batch.add_column(sa.Column("source_domain", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("fashion_assets") as batch:
        batch.drop_column("source_domain")
        batch.drop_column("source_image_url")
        batch.drop_column("source_url")
