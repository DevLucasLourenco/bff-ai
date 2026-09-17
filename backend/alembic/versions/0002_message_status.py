"""estado explicito da mensagem do assistente (F3.1)

Antes, uma resposta interrompida no meio era descartada por inteiro: a mensagem
do usuario ja estava commitada e a conversa ficava com um turno pendurado sem
nada que explicasse. `status` + `error_code`/`error_message` permitem persistir a
resposta parcial e mostra-la marcada na UI.

As CHECK constraints de role e status entram junto porque o SQLite so aceita
adicionar constraint recriando a tabela, e esta migration ja mexe em `messages`.
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_message_status"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("messages", recreate="always") as batch:
        batch.add_column(
            sa.Column("status", sa.String(20), nullable=False, server_default="complete")
        )
        batch.add_column(sa.Column("error_code", sa.String(40), nullable=True))
        batch.add_column(sa.Column("error_message", sa.Text(), nullable=True))
        batch.create_check_constraint("ck_messages_role", "role in ('user', 'assistant')")
        batch.create_check_constraint(
            "ck_messages_status", "status in ('complete', 'failed', 'cancelled')"
        )


def downgrade():
    with op.batch_alter_table("messages", recreate="always") as batch:
        batch.drop_constraint("ck_messages_status", type_="check")
        batch.drop_constraint("ck_messages_role", type_="check")
        batch.drop_column("error_message")
        batch.drop_column("error_code")
        batch.drop_column("status")
