"""Defeitos encontrados na auditoria de 2026-09-18.

Cada teste descreve o comportamento correto. Foram escritos ANTES da correção e
falhavam — ficam aqui como trava contra regressão.
"""


def modelo_nim(client, model_id="meta/llama-3.1"):
    nim = next(p for p in client.get("/api/providers").json() if p["kind"] == "nvidia_nim")
    return client.post("/api/models", json={
        "provider_id": nim["id"], "display_name": model_id.split("/")[-1], "model_id": model_id,
        "temperature": 0.7, "top_p": 0.9,
    })


# ---------------------------------------------------- duplicidade de modelo


def test_adicionar_o_mesmo_modelo_duas_vezes_nao_e_erro_500(client):
    """Clicar duas vezes no mesmo modelo da lista remota estourava IntegrityError."""
    assert modelo_nim(client).status_code == 201
    segunda = modelo_nim(client)
    assert segunda.status_code != 500
    assert segunda.status_code in (200, 201, 409)


def test_readicionar_modelo_excluido_traz_ele_de_volta(client):
    """Modelo arquivado ainda ocupava a UNIQUE (provider, model_id): re-adicionar dava 500."""
    criado = modelo_nim(client).json()
    client.delete(f"/api/models/{criado['id']}")

    de_novo = modelo_nim(client)
    assert de_novo.status_code in (200, 201)
    assert de_novo.json()["model_id"] == "meta/llama-3.1"
    assert "meta/llama-3.1" in [m["model_id"] for m in client.get("/api/models").json()]


# ---------------------------------------------------- nome de persona excluída


def test_recriar_persona_com_nome_de_uma_excluida(client):
    """Persona arquivada ainda ocupava o nome: criar outra 'Coach' dava 409."""
    coach = client.post("/api/personas", json={"name": "Coach"}).json()
    client.delete(f"/api/personas/{coach['id']}")

    nova = client.post("/api/personas", json={"name": "Coach"})
    assert nova.status_code == 201


# ------------------------------------------ itens arquivados não podem ser usados


def test_nao_ativa_modelo_arquivado(client):
    extra = modelo_nim(client).json()
    client.delete(f"/api/models/{extra['id']}")
    assert client.post(f"/api/models/{extra['id']}/activate").status_code == 404


def test_nao_cria_conversa_com_persona_arquivada(client):
    coach = client.post("/api/personas", json={"name": "Coach"}).json()
    client.delete(f"/api/personas/{coach['id']}")
    assert client.post("/api/conversations", json={"persona_id": coach["id"]}).status_code == 404


def test_nao_cria_conversa_com_modelo_arquivado(client):
    extra = modelo_nim(client).json()
    client.delete(f"/api/models/{extra['id']}")
    assert client.post("/api/conversations", json={"model_config_id": extra["id"]}).status_code == 404


def test_settings_nao_aceita_persona_ou_modelo_arquivado(client):
    coach = client.post("/api/personas", json={"name": "Coach"}).json()
    client.delete(f"/api/personas/{coach['id']}")
    assert client.patch("/api/settings", json={"active_persona_id": coach["id"]}).status_code == 404


# ------------------------------------------------------------ memória


def test_mudar_memoria_para_global_limpa_o_alvo(client):
    """Voltar uma memória de persona para global deixava persona_id pendurado."""
    persona = client.get("/api/personas").json()[0]
    memoria = client.post("/api/memories", json={
        "category": "x", "content": "y", "scope": "persona", "persona_id": persona["id"],
    }).json()

    atualizada = client.patch(f"/api/memories/{memoria['id']}", json={"scope": "global"}).json()
    assert atualizada["scope"] == "global"
    assert atualizada["persona_id"] is None


# ------------------------------------------------------------ regenerar


def test_regenerar_resposta_antiga_nao_apaga_o_resto_da_conversa(client, fake_adapter, db):
    """O botão aparecia em toda resposta e apagava (hard delete) tudo depois dela,
    inclusive mensagens da usuária, sem confirmação."""
    from app.domain.models import Message

    conversa = client.post("/api/conversations", json={}).json()["id"]
    for texto in ("primeira", "segunda", "terceira"):
        fake_adapter(chunks=(f"resposta a {texto}",))
        client.post(f"/api/conversations/{conversa}/messages/stream", json={"content": texto})

    primeira_resposta = db.query(Message).filter_by(conversation_id=conversa, role="assistant").order_by(Message.id).first()
    fake_adapter(chunks=("refeita",))
    resposta = client.post(f"/api/conversations/{conversa}/messages/{primeira_resposta.id}/regenerate")

    assert resposta.status_code == 409
    db.expire_all()
    assert db.query(Message).filter_by(conversation_id=conversa).count() == 6


def test_regenerar_a_ultima_resposta_continua_funcionando(client, fake_adapter, db):
    from app.domain.models import Message

    conversa = client.post("/api/conversations", json={}).json()["id"]
    fake_adapter(chunks=("primeira versão",))
    client.post(f"/api/conversations/{conversa}/messages/stream", json={"content": "oi"})
    ultima = db.query(Message).filter_by(conversation_id=conversa, role="assistant").one()

    fake_adapter(chunks=("segunda versão",))
    assert client.post(f"/api/conversations/{conversa}/messages/{ultima.id}/regenerate").status_code == 200


# ------------------------------------------------- campos que não faziam nada


def test_nome_da_usuaria_chega_ao_prompt(client, fake_adapter):
    """'Como chamar a usuária' era salvo e nunca lido."""
    client.patch("/api/settings", json={"user_display_name": "Lucas"})
    conversa = client.post("/api/conversations", json={}).json()["id"]
    adapter = fake_adapter()
    client.post(f"/api/conversations/{conversa}/messages/stream", json={"content": "oi"})
    system = next(m["content"] for m in adapter.received_messages if m["role"] == "system")
    assert "Lucas" in system


def test_nome_da_usuaria_vazio_nao_polui_o_prompt(client, fake_adapter):
    client.patch("/api/settings", json={"user_display_name": ""})
    conversa = client.post("/api/conversations", json={}).json()["id"]
    adapter = fake_adapter()
    client.post(f"/api/conversations/{conversa}/messages/stream", json={"content": "oi"})
    system = next(m["content"] for m in adapter.received_messages if m["role"] == "system")
    assert "Chame a usuária" not in system


def test_conversa_expoe_a_saudacao_da_persona(client):
    """A saudação da persona era editável e nunca aparecia."""
    conversa = client.post("/api/conversations", json={}).json()
    assert conversa["persona_greeting"].startswith("Oii")


# ------------------------------------------------- sinal de vida no stream


def test_stream_lento_manda_sinal_de_vida_e_termina_completo(client, fake_adapter, monkeypatch, db):
    """Sem batimento, o navegador não distinguia 'modelo pensando' de 'conexão
    morta', e uma conexão que morria em silêncio deixava a UI travada."""
    from app.domain.models import Message

    monkeypatch.setattr("app.services.chat.HEARTBEAT_SECONDS", 0.05)
    fake_adapter(chunks=("a", "b"), delay=0.25)
    conversa = client.post("/api/conversations", json={}).json()["id"]

    corpo = client.post(f"/api/conversations/{conversa}/messages/stream", json={"content": "oi"}).text

    assert ": ping" in corpo
    assistente = db.query(Message).filter_by(conversation_id=conversa, role="assistant").one()
    assert assistente.content == "ab"          # os pings não viram texto
    assert assistente.status == "complete"


def test_stream_rapido_nao_manda_ping(client, fake_adapter):
    fake_adapter(chunks=("a", "b"))
    conversa = client.post("/api/conversations", json={}).json()["id"]
    corpo = client.post(f"/api/conversations/{conversa}/messages/stream", json={"content": "oi"}).text
    assert ": ping" not in corpo
