"""Prova que a infra de teste exercita o app real (F6.1)."""


def test_lifespan_verifica_schema_e_semeia_defaults(client):
    # O TestClient roda o lifespan: se verify_schema falhasse, nem chegaria aqui.
    assert client.get("/health").json() == {"status": "ok"}

    settings = client.get("/api/settings").json()
    assert settings["app_name"] == "BFF AI"
    # O nome da assistente mora na persona, não em settings.
    assert "assistant_display_name" not in settings


def test_bootstrap_cria_persona_e_providers(client):
    personas = client.get("/api/personas").json()
    assert [p["name"] for p in personas] == ["Bestie"]

    providers = client.get("/api/providers").json()
    assert {p["kind"] for p in providers} == {"ollama", "nvidia_nim"}
    # A API nunca devolve a chave em si, só se existe uma.
    assert all("api_key" not in p for p in providers)


def test_banco_limpo_entre_testes(client):
    assert client.get("/api/conversations").json() == []
    created = client.post("/api/conversations", json={}).json()
    assert created["persona_name"] == "Bestie"
    assert len(client.get("/api/conversations").json()) == 1


def test_health_ready_checa_banco_e_chave_mestra(client):
    corpo = client.get("/health/ready").json()
    assert corpo["status"] == "ok"
    assert corpo["checks"]["database"]["ok"] is True
    assert corpo["checks"]["database"]["revision"] == corpo["checks"]["database"]["expected"]
    assert corpo["checks"]["master_key"]["ok"] is True


def test_health_ready_denuncia_chave_mestra_trocada(client, monkeypatch):
    from cryptography.fernet import Fernet

    ollama = next(p for p in client.get("/api/providers").json() if p["kind"] == "ollama")
    client.patch(f"/api/providers/{ollama['id']}", json={"api_key": "nvapi-teste"})

    # Outra chave: os segredos guardados deixam de abrir.
    outra = Fernet.generate_key().decode()
    monkeypatch.setattr("app.core.security.APP_MASTER_KEY", outra)

    resposta = client.get("/health/ready")
    assert resposta.status_code == 503
    assert resposta.json()["checks"]["master_key"]["ok"] is False
