"""remove redundant global Fashion toggle

Revision ID: 0006_remove_global_fashion_setting
Revises: 0005_chat_fashion_attachments
"""

from alembic import op

revision = "0006_remove_global_fashion_setting"
down_revision = "0005_chat_fashion_attachments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM app_settings WHERE key = 'fashion_enabled'")


def downgrade() -> None:
    op.execute("INSERT INTO app_settings (key, value, updated_at) VALUES ('fashion_enabled', 'false', CURRENT_TIMESTAMP)")
