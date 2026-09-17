"""initial schema"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("provider_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_provider_configs_kind", "provider_configs", ["kind"])
    op.create_table("personas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.String(400), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("greeting", sa.Text(), nullable=False),
        sa.Column("avatar_emoji", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table("memories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memories_category", "memories", ["category"])
    op.create_index("ix_memories_is_active", "memories", ["is_active"])
    op.create_table("app_settings",
        sa.Column("key", sa.String(120), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table("model_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("provider_configs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("model_id", sa.String(240), nullable=False),
        sa.Column("temperature_milli", sa.Integer(), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=False),
        sa.Column("top_p_milli", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider_id", "model_id", name="uq_provider_model"),
    )
    op.create_index("ix_model_configs_provider_id", "model_configs", ["provider_id"])
    op.create_table("conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("persona_id", sa.Integer(), sa.ForeignKey("personas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("model_config_id", sa.Integer(), sa.ForeignKey("model_configs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conversations_persona_id", "conversations", ["persona_id"])
    op.create_index("ix_conversations_model_config_id", "conversations", ["model_config_id"])
    op.create_index("ix_conversations_is_archived", "conversations", ["is_archived"])
    op.create_table("messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_id", sa.String(240), nullable=True),
        sa.Column("provider_kind", sa.String(40), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])


def downgrade():
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("model_configs")
    op.drop_table("app_settings")
    op.drop_table("memories")
    op.drop_table("personas")
    op.drop_table("provider_configs")
