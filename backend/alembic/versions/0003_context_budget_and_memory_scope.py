"""orcamento de contexto e escopo de memoria (F4.2, F4.3)

context_window: sem ele nao ha como truncar historico, e uma conversa longa
crescia ate estourar a janela do modelo e parar de funcionar.

scope/persona_id/conversation_id em memories: antes toda memoria ativa entrava
em toda requisicao, de qualquer persona e de qualquer conversa.
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_context_budget_and_memory_scope"
down_revision = "0002_message_status"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("model_configs") as batch:
        batch.add_column(sa.Column("context_window", sa.Integer(), nullable=False, server_default="0"))

    with op.batch_alter_table("memories", recreate="always") as batch:
        batch.add_column(sa.Column("scope", sa.String(20), nullable=False, server_default="global"))
        batch.add_column(sa.Column("persona_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("conversation_id", sa.Integer(), nullable=True))
        batch.create_check_constraint(
            "ck_memories_scope", "scope in ('global', 'persona', 'conversation')"
        )
        batch.create_foreign_key(
            "fk_memories_persona", "personas", ["persona_id"], ["id"], ondelete="CASCADE"
        )
        batch.create_foreign_key(
            "fk_memories_conversation", "conversations", ["conversation_id"], ["id"], ondelete="CASCADE"
        )
    op.create_index("ix_memories_scope", "memories", ["scope"])
    op.create_index("ix_memories_persona_id", "memories", ["persona_id"])
    op.create_index("ix_memories_conversation_id", "memories", ["conversation_id"])


def downgrade():
    op.drop_index("ix_memories_conversation_id", table_name="memories")
    op.drop_index("ix_memories_persona_id", table_name="memories")
    op.drop_index("ix_memories_scope", table_name="memories")
    with op.batch_alter_table("memories", recreate="always") as batch:
        batch.drop_constraint("fk_memories_conversation", type_="foreignkey")
        batch.drop_constraint("fk_memories_persona", type_="foreignkey")
        batch.drop_constraint("ck_memories_scope", type_="check")
        batch.drop_column("conversation_id")
        batch.drop_column("persona_id")
        batch.drop_column("scope")
    with op.batch_alter_table("model_configs") as batch:
        batch.drop_column("context_window")
