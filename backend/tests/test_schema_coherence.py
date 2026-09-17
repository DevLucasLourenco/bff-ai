"""Trava contra divergência entre models e migrations (F1.3).

Este teste existe porque o defeito que a Fase 1 consertou — schema com duas
fontes de verdade — volta em silêncio na primeira coluna adicionada sem
migration. Aqui ele vira vermelho.
"""

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext

from app.db.base import Base
from app.db.schema import current_revision, head_revision
from app.db.session import engine
from app.domain import models  # noqa: F401  (registra os modelos no metadata)


def test_banco_migrado_bate_exatamente_com_os_models():
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert diff == [], f"models e migrations divergiram: {diff}"


def test_banco_de_teste_esta_na_revisao_head():
    assert current_revision(engine) == head_revision()
