"""Infra de teste (F6.1).

Regras deste arquivo:

- nenhum teste toca o banco real (`backend/data/bff_ai.db`) nem a APP_MASTER_KEY
  real: as duas variáveis são substituídas **antes** de qualquer import de `app`,
  porque `app.core.config` lê o ambiente no momento do import;
- nenhum teste faz I/O de rede: quem fala com provider é o FakeAdapter;
- o schema do banco de teste vem de `alembic upgrade head`, não de `create_all` —
  assim os testes exercitam o mesmo caminho do deploy.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet

_TMP_DIR = Path(tempfile.mkdtemp(prefix="bff-ai-tests-"))
_TMP_DB = _TMP_DIR / "test.db"

# Precede qualquer import de app.*  — load_dotenv() não sobrescreve o que já está
# no ambiente, então a chave real do .env nunca entra nos testes.
os.environ["BFF_DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
os.environ["APP_MASTER_KEY"] = Fernet.generate_key().decode()

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.schema import alembic_config  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.domain.models import (  # noqa: E402
    AppSetting,
    Conversation,
    Memory,
    Message,
    ModelConfig,
    Persona,
    ProviderConfig,
)
from app.main import app  # noqa: E402
from app.services.bootstrap import bootstrap  # noqa: E402
from tests.fakes import FakeAdapter  # noqa: E402

# Ordem de deleção respeita as FKs (filhos primeiro).
_TABLES_IN_FK_ORDER = (Message, Conversation, ModelConfig, ProviderConfig, Persona, Memory, AppSetting)


@pytest.fixture(scope="session", autouse=True)
def _migrated_database():
    """Sobe o schema uma vez por sessão, pelo mesmo comando que o deploy usa."""
    # Comparação em forma posix: no Windows, str(Path) usa barra invertida e a
    # URL do SQLAlchemy não.
    assert _TMP_DB.as_posix() in str(engine.url), "os testes precisam apontar para o banco temporário"
    command.upgrade(alembic_config(), "head")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_database(_migrated_database):
    """Cada teste começa com o banco recém-semeado, sem resíduo do anterior."""
    with SessionLocal() as db:
        for model in _TABLES_IN_FK_ORDER:
            db.query(model).delete()
        db.commit()
        bootstrap(db)
    yield


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    # O TestClient dispara o lifespan real, então verify_schema() também é testado.
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def fake_adapter(monkeypatch):
    """Instala um FakeAdapter no lugar do provider real.

    Devolve uma função: `install(chunks=..., fail_after=...) -> FakeAdapter`.
    """

    def install(**kwargs) -> FakeAdapter:
        adapter = FakeAdapter(**kwargs)
        monkeypatch.setattr("app.services.chat.create_adapter", lambda kind: adapter)
        return adapter

    return install
