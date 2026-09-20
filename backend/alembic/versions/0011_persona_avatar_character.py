"""associate an illustrated character with each persona

Revision ID: 0011_persona_avatar_character
Revises: 0010_fashion_asset_sources
"""

from alembic import op
import sqlalchemy as sa

revision = "0011_persona_avatar_character"
down_revision = "0010_fashion_asset_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("personas") as batch:
        batch.add_column(sa.Column("avatar_character", sa.String(length=40), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("personas") as batch:
        batch.drop_column("avatar_character")
