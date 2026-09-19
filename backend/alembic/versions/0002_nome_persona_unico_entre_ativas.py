"""nome de persona unico so entre as ativas

Com o soft delete, uma persona excluida continuava ocupando o nome no UNIQUE da
coluna, e criar outra persona com o mesmo nome falhava. Vira indice parcial:
unico apenas onde is_archived = 0.

A UNIQUE original foi criada sem nome (`sa.UniqueConstraint('name')`). O SQLite
so remove constraint recriando a tabela, e o modo batch do Alembic so consegue
apontar para uma constraint sem nome se uma naming_convention lhe der um.
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_nome_persona_ativa"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

CONVENCAO = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def upgrade():
    with op.batch_alter_table("personas", naming_convention=CONVENCAO, recreate="always") as batch:
        batch.drop_constraint("uq_personas_name", type_="unique")
    op.create_index(
        "uq_personas_nome_ativa", "personas", ["name"], unique=True,
        sqlite_where=sa.text("is_archived = 0"),
    )


def downgrade():
    op.drop_index("uq_personas_nome_ativa", table_name="personas")
    with op.batch_alter_table("personas", naming_convention=CONVENCAO, recreate="always") as batch:
        batch.create_unique_constraint("uq_personas_name", ["name"])
