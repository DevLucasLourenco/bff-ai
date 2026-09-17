"""Providers, segredos e a regra de "sem fallback" (F6.2)."""

import pytest

from app.core.security import SecretCipher
from app.domain.models import ProviderConfig
from app.services.llm.errors import ProviderUnreachable, UnsupportedProviderError
from app.services.llm.factory import ADAPTERS, capabilities_for, create_adapter
from app.services.llm.nvidia_nim import NvidiaNimAdapter
from app.services.llm.ollama import OllamaAdapter

SEGREDO = "nvapi-chave-super-secreta-123"


def test_factory_mapeia_provider_exato_sem_fallback():
    assert isinstance(create_adapter("ollama"), OllamaAdapter)
    assert isinstance(create_adapter("nvidia_nim"), NvidiaNimAdapter)
    with pytest.raises(UnsupportedProviderError):
        create_adapter("inexistente")


def test_registry_e_a_unica_lista_de_kinds():
    from app.domain.schemas import ProviderKind
    from typing import get_args

    assert set(get_args(ProviderKind)) == set(ADAPTERS)


def test_kind_invalido_e_recusado_na_criacao(client):
    resposta = client.post("/api/providers", json={
        "name": "Qualquer", "kind": "openai", "base_url": "https://exemplo.test/v1",
    })
    assert resposta.status_code == 422


def test_api_key_e_guardada_cifrada_e_nunca_devolvida(client, db):
    ollama = next(p for p in client.get("/api/providers").json() if p["kind"] == "ollama")
    corpo = client.patch(f"/api/providers/{ollama['id']}", json={"api_key": SEGREDO}).json()

    assert corpo["has_api_key"] is True
    assert SEGREDO not in str(corpo)

    row = db.get(ProviderConfig, ollama["id"])
    assert row.api_key_encrypted and SEGREDO not in row.api_key_encrypted
    assert SecretCipher().decrypt(row.api_key_encrypted) == SEGREDO


def test_erro_ao_consultar_modelos_nao_vaza_a_chave(client, monkeypatch):
    ollama = next(p for p in client.get("/api/providers").json() if p["kind"] == "ollama")
    client.patch(f"/api/providers/{ollama['id']}", json={"api_key": SEGREDO})

    class AdapterQueFalha:
        capabilities = capabilities_for("ollama")

        async def list_models(self, base_url, api_key):
            raise ProviderUnreachable(
                f"Não foi possível falar com o provider em {base_url}.",
                provider_detail="connection refused",
            )

    monkeypatch.setattr("app.api.routes.providers.create_adapter", lambda kind: AdapterQueFalha())
    resposta = client.get(f"/api/providers/{ollama['id']}/remote-models")

    assert resposta.status_code == 503
    assert SEGREDO not in resposta.text
    assert resposta.json()["detail"]["code"] == "provider_unreachable"


def test_capacidades_sao_declaradas_pelo_adapter():
    assert capabilities_for("ollama").honors_max_tokens is True
    assert capabilities_for("nvidia_nim").honors_max_tokens is False
    assert capabilities_for("nvidia_nim").default_reasoning_effort == "none"
