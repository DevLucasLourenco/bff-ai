import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# env.py vive em backend/alembic/, então backend/ é o parent do parent. Resolver
# isso pelo __file__ torna o alembic independente do cwd — `prepend_sys_path = .`
# só funcionava rodando de dentro de backend/.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import DATABASE_URL  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.domain import models  # noqa: E402,F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# A URL vem do mesmo config que o app usa (caminho absoluto). Antes vinha do
# alembic.ini como `sqlite:///data/bff_ai.db`, relativo ao cwd: rodar alembic de
# fora de backend/ migrava um banco diferente do que o app abria.
# O escape de % protege a interpolação do configparser.
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))
target_metadata = Base.metadata

# render_as_batch é obrigatório no SQLite: sem ele, qualquer ALTER COLUMN futuro
# falha, porque o SQLite não suporta o comando e o alembic precisa recriar a
# tabela. As fases 3 e 4 do roadmap dependem disso.
BATCH = True


def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=BATCH,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=BATCH)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
