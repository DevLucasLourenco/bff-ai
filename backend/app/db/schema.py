from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine

BACKEND_DIR = Path(__file__).resolve().parents[2]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"

UPGRADE_HINT = f"alembic -c {ALEMBIC_INI.name} upgrade head  (de dentro de backend/)"


class SchemaOutOfDateError(RuntimeError):
    """O banco não está na revisão que o código espera."""


def alembic_config() -> Config:
    # script_location no .ini usa %(here)s, então resolve a partir do próprio
    # arquivo — funciona de qualquer cwd.
    return Config(str(ALEMBIC_INI))


def head_revision() -> str | None:
    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def current_revision(engine: Engine) -> str | None:
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def verify_schema(engine: Engine) -> None:
    """Falha cedo e com instrução, em vez de falhar tarde com 'no such column'.

    Substitui o antigo Base.metadata.create_all(): create_all criava tabelas
    faltantes mas nunca alterava as existentes, então uma coluna nova no modelo
    simplesmente não chegava ao banco e o erro aparecia em runtime.
    """
    head = head_revision()
    current = current_revision(engine)
    if current == head:
        return
    if current is None:
        raise SchemaOutOfDateError(
            f"O banco em {engine.url.database} ainda não foi migrado. Rode: {UPGRADE_HINT}"
        )
    raise SchemaOutOfDateError(
        f"O banco está na revisão {current}, mas o código espera {head}. Rode: {UPGRADE_HINT}"
    )
