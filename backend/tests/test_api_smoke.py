"""Prova que a infra de teste exercita o app real (F6.1)."""


def test_lifespan_verifica_schema_e_semeia_defaults(client):
    # O TestClient roda o lifespan: se verify_schema falhasse, nem chegaria aqui.
    assert client.get("/health").json() == {"status": "ok"}

    settings = client.get("/api/settings").json()
    assert settings["app_name"] == "BFF AI"
    assert settings["assistant_display_name"] == "Bestie"


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
