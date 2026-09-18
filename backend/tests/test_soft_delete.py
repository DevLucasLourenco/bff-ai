"""Exclusão é sempre soft: some da lista, a linha fica.

O ponto central: **nada ligado ao item excluído é removido**. As FKs com
CASCADE/RESTRICT continuam no schema como rede de segurança contra um DELETE
feito por fora da API, mas pelo app elas nunca disparam, porque o app nunca
apaga de verdade.
"""

from app.domain.models import Conversation, Memory, Message, ModelConfig, Persona


def nova_conversa(client, **kwargs) -> int:
    return client.post("/api/conversations", json=kwargs).json()["id"]


# ------------------------------------------------------------------- personas


def test_excluir_persona_some_da_lista_mas_a_linha_fica(client, db):
    client.post("/api/personas", json={"name": "Coach", "personality": "direta"})
    coach = next(p for p in client.get("/api/personas").json() if p["name"] == "Coach")

    assert client.delete(f"/api/personas/{coach['id']}").status_code == 204

    assert "Coach" not in [p["name"] for p in client.get("/api/personas").json()]
    linha = db.get(Persona, coach["id"])
    assert linha is not None and linha.is_archived is True


def test_excluir_persona_nao_apaga_nada_ligado_a_ela(client, db, fake_adapter):
    """A pergunta central: o que acontece com o que aponta para a persona."""
    client.post("/api/personas", json={"name": "Coach", "personality": "direta"})
    coach = next(p for p in client.get("/api/personas").json() if p["name"] == "Coach")

    conversa = nova_conversa(client, persona_id=coach["id"])
    fake_adapter()
    client.post(f"/api/conversations/{conversa}/messages/stream", json={"content": "oi"})
    memoria = client.post("/api/memories", json={
        "category": "ctx", "content": "memória da Coach", "scope": "persona", "persona_id": coach["id"],
    }).json()

    client.delete(f"/api/personas/{coach['id']}")
    db.expire_all()

    # Conversa intacta, ainda apontando para a persona arquivada.
    viva = db.get(Conversation, conversa)
    assert viva is not None and viva.persona_id == coach["id"]
    # Mensagens intactas.
    assert db.query(Message).filter_by(conversation_id=conversa).count() == 2
    # Memória no escopo dela intacta.
    assert db.get(Memory, memoria["id"]) is not None


def test_conversa_de_persona_arquivada_continua_respondendo(client, db, fake_adapter):
    client.post("/api/personas", json={"name": "Coach", "personality": "objetiva e direta"})
    coach = next(p for p in client.get("/api/personas").json() if p["name"] == "Coach")
    conversa = nova_conversa(client, persona_id=coach["id"])

    client.delete(f"/api/personas/{coach['id']}")

    adapter = fake_adapter()
    resposta = client.post(f"/api/conversations/{conversa}/messages/stream", json={"content": "oi"})
    assert resposta.status_code == 200
    # O prompt da persona arquivada continua sendo usado por quem já a usava.
    system = next(m["content"] for m in adapter.received_messages if m["role"] == "system")
    assert "objetiva e direta" in system


def test_nao_da_para_arquivar_a_unica_persona(client):
    unica = client.get("/api/personas").json()[0]
    assert client.delete(f"/api/personas/{unica['id']}").status_code == 409


def test_arquivar_a_persona_padrao_promove_outra(client):
    client.post("/api/personas", json={"name": "Coach"})
    padrao_id = client.get("/api/settings").json()["active_persona_id"]

    client.delete(f"/api/personas/{padrao_id}")

    novo_padrao = client.get("/api/settings").json()["active_persona_id"]
    assert novo_padrao != padrao_id
    # E aponta para uma persona que ainda está na lista.
    assert novo_padrao in [p["id"] for p in client.get("/api/personas").json()]


# --------------------------------------------------------------------- modelos


def test_excluir_modelo_some_da_lista_mas_a_conversa_sobrevive(client, db, fake_adapter):
    extra = client.post("/api/models", json={
        "provider_id": 1, "display_name": "Descartável", "model_id": "llama3.2:extra",
        "temperature": 0.7, "top_p": 0.9,
    }).json()
    conversa = nova_conversa(client, model_config_id=extra["id"])
    fake_adapter()
    client.post(f"/api/conversations/{conversa}/messages/stream", json={"content": "oi"})

    assert client.delete(f"/api/models/{extra['id']}").status_code == 204

    assert extra["id"] not in [m["id"] for m in client.get("/api/models").json()]
    db.expire_all()
    assert db.get(ModelConfig, extra["id"]).is_archived is True
    # A conversa continua legível, com o modelo que ela registrou.
    assert client.get(f"/api/conversations/{conversa}").json()["model_display_name"] == "Descartável"


def test_arquivar_o_modelo_ativo_promove_outro(client):
    extra = client.post("/api/models", json={
        "provider_id": 1, "display_name": "Extra", "model_id": "llama3.2:extra",
        "temperature": 0.7, "top_p": 0.9,
    }).json()
    client.post(f"/api/models/{extra['id']}/activate")

    client.delete(f"/api/models/{extra['id']}")

    ativo = client.get("/api/settings").json()["active_model_config_id"]
    assert ativo != extra["id"]
    assert ativo in [m["id"] for m in client.get("/api/models").json()]


def test_nao_da_para_arquivar_o_unico_modelo(client):
    unico = client.get("/api/models").json()[0]
    assert client.delete(f"/api/models/{unico['id']}").status_code == 409


# ------------------------------------------------------------------- conversas


def test_excluir_conversa_preserva_as_mensagens(client, db, fake_adapter):
    conversa = nova_conversa(client)
    fake_adapter()
    client.post(f"/api/conversations/{conversa}/messages/stream", json={"content": "oi"})

    assert client.delete(f"/api/conversations/{conversa}").status_code == 204

    assert conversa not in [c["id"] for c in client.get("/api/conversations").json()]
    db.expire_all()
    assert db.get(Conversation, conversa).is_archived is True
    assert db.query(Message).filter_by(conversation_id=conversa).count() == 2


def test_conversa_arquivada_recusa_novas_mensagens(client, fake_adapter):
    conversa = nova_conversa(client)
    client.delete(f"/api/conversations/{conversa}")
    fake_adapter()
    assert client.post(
        f"/api/conversations/{conversa}/messages/stream", json={"content": "oi"}
    ).status_code == 409


# ------------------------------------------------- max_tokens sem sentinela


def test_max_tokens_ausente_e_null_no_banco_nao_zero(client, db):
    criado = client.post("/api/models", json={
        "provider_id": 1, "display_name": "Sem teto", "model_id": "llama3.2:sem-teto",
        "temperature": 0.7, "top_p": 0.9,
    }).json()
    assert criado["max_tokens"] is None
    # O sentinela 0 não existe mais: a coluna guarda NULL.
    assert db.get(ModelConfig, criado["id"]).max_tokens is None
