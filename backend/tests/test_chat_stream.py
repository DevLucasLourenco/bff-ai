"""Comportamento crítico do fluxo de chat (F6.2).

Cobre exatamente as regras que o README declara inegociáveis — são as que não
podem regredir em silêncio.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from app.domain.models import Conversation, Message, MessageStatus, ModelConfig
from app.services.llm.base import ProviderCapabilities
from app.services.llm.errors import ProviderAuthError


def sse_events(raw: str) -> list[tuple[str, dict]]:
    events = []
    for frame in raw.split("\n\n"):
        if not frame.strip():
            continue
        event = next((l[7:] for l in frame.splitlines() if l.startswith("event: ")), None)
        data = next((l[6:] for l in frame.splitlines() if l.startswith("data: ")), None)
        if event and data:
            events.append((event, json.loads(data)))
    return events


def new_conversation(client) -> int:
    return client.post("/api/conversations", json={}).json()["id"]


def send(client, conversation_id: int, content: str = "oi"):
    return client.post(f"/api/conversations/{conversation_id}/messages/stream", json={"content": content})


# --------------------------------------------------------------- caminho feliz


def test_resposta_completa_e_persistida_com_metadados(client, fake_adapter, db):
    fake_adapter(chunks=("Oi", " você", "!"))
    conversation_id = new_conversation(client)

    events = sse_events(send(client, conversation_id, "tudo bem?").text)
    kinds = [name for name, _ in events]
    assert kinds[0] == "meta"
    assert kinds[-1] == "done"
    assert "".join(payload["text"] for name, payload in events if name == "token") == "Oi você!"

    messages = db.query(Message).filter_by(conversation_id=conversation_id).order_by(Message.id).all()
    assert [(m.role, m.content, m.status) for m in messages] == [
        ("user", "tudo bem?", "complete"),
        ("assistant", "Oi você!", "complete"),
    ]
    assert messages[1].latency_ms is not None
    assert messages[1].provider_kind == "ollama"


def test_titulo_vem_da_primeira_mensagem(client, fake_adapter, db):
    fake_adapter()
    conversation_id = new_conversation(client)
    send(client, conversation_id, "me ajuda com o currículo")
    assert db.get(Conversation, conversation_id).title == "me ajuda com o currículo"


# ------------------------------------------------------- F3.1 resposta parcial


def test_falha_no_meio_persiste_o_parcial_e_nao_tenta_de_novo(client, fake_adapter, db):
    adapter = fake_adapter(
        chunks=("Começo", " da", " resposta", " que", " some"),
        fail_after=3,
        error=ProviderAuthError("Chave recusada", provider_detail="401 unauthorized"),
    )
    conversation_id = new_conversation(client)

    events = sse_events(send(client, conversation_id).text)
    name, payload = events[-1]
    assert name == "error"
    assert payload["code"] == "provider_auth"
    assert payload["message"] == "Chave recusada"
    # provider_detail vem separado da mensagem que a usuária lê.
    assert payload["provider_detail"] == "401 unauthorized"

    assistant = db.query(Message).filter_by(conversation_id=conversation_id, role="assistant").one()
    assert assistant.status == MessageStatus.FAILED.value
    assert assistant.content == "Começo da resposta"  # o parcial sobreviveu
    assert assistant.error_code == "provider_auth"

    # Regra 1: uma única tentativa, nenhum outro provider.
    assert adapter.received_config is not None


def test_mensagem_falhada_nao_volta_como_contexto(client, fake_adapter, db):
    fake_adapter(chunks=("a", "b", "c"), fail_after=1)
    conversation_id = new_conversation(client)
    send(client, conversation_id, "primeira")

    adapter = fake_adapter(chunks=("ok",))
    send(client, conversation_id, "segunda")

    roles_e_textos = [(m["role"], m["content"]) for m in adapter.received_messages]
    assert ("assistant", "a") not in roles_e_textos
    assert [c for r, c in roles_e_textos if r == "user"] == ["primeira", "segunda"]


# ------------------------------------------------- F2.1 capacidades do provider


def test_ollama_honra_max_tokens_e_nao_pede_usage(client, fake_adapter, db):
    adapter = fake_adapter()
    conversation_id = new_conversation(client)
    send(client, conversation_id)

    config = adapter.received_config
    assert config.max_tokens == 2048           # o modelo semeado pelo bootstrap
    assert config.reasoning_effort is None
    assert config.include_usage is False


def test_nvidia_nim_ignora_max_tokens_e_desliga_reasoning(client, fake_adapter, db):
    nim = next(p for p in client.get("/api/providers").json() if p["kind"] == "nvidia_nim")
    model = client.post("/api/models", json={
        "provider_id": nim["id"], "display_name": "NIM", "model_id": "meta/llama-3.1",
        "temperature": 0.5, "max_tokens": 2048, "top_p": 0.9,
    }).json()
    # A rota ja reporta max_tokens como automatico para este provider.
    assert model["max_tokens"] is None

    conversation_id = client.post("/api/conversations", json={"model_config_id": model["id"]}).json()["id"]
    adapter = fake_adapter()
    send(client, conversation_id)

    config = adapter.received_config
    assert config.max_tokens is None
    assert config.reasoning_effort == "none"
    assert config.include_usage is True


# ------------------------------------------------------------ F4.1/F4.3 prompt


def test_prompt_comeca_pela_regra_global_e_so_traz_memoria_no_escopo(client, fake_adapter, db):
    conversation_id = new_conversation(client)
    outra = new_conversation(client)
    client.post("/api/memories", json={"category": "pref", "content": "gosta de café", "scope": "global"})
    client.post("/api/memories", json={
        "category": "pref", "content": "segredo da outra conversa",
        "scope": "conversation", "conversation_id": outra,
    })

    adapter = fake_adapter()
    send(client, conversation_id)

    system_blocks = [m["content"] for m in adapter.received_messages if m["role"] == "system"]
    # O primeiro bloco é o prompt composto: regra global, depois a persona.
    assert system_blocks[0].startswith("Estas regras valem para todas as personas")
    assert "Você é Bestie." in system_blocks[0]
    assert "gosta de café" in system_blocks[1]
    assert "segredo da outra conversa" not in " ".join(system_blocks)


def test_memoria_de_persona_nao_vaza_para_outra_persona(client, fake_adapter, db):
    outra_persona = client.post("/api/personas", json={
        "name": "Coach", "description": "", "personality": "objetiva e direta",
        "greeting": "", "avatar_emoji": "🎯",
    }).json()
    client.post("/api/memories", json={
        "category": "ctx", "content": "memoria exclusiva da Coach",
        "scope": "persona", "persona_id": outra_persona["id"],
    })

    conversation_id = new_conversation(client)  # usa a persona padrao (Bestie)
    adapter = fake_adapter()
    send(client, conversation_id)
    assert "memoria exclusiva da Coach" not in json.dumps(adapter.received_messages)


def test_memoria_com_escopo_exige_alvo_valido(client):
    resposta = client.post("/api/memories", json={
        "category": "x", "content": "y", "scope": "persona", "persona_id": 9999,
    })
    assert resposta.status_code == 422


# --------------------------------------------------------- F4.2 truncamento


def test_historico_longo_e_truncado_com_aviso(client, fake_adapter, db):
    modelo = client.get("/api/models").json()[0]
    client.patch(f"/api/models/{modelo['id']}", json={"context_window": 400})

    conversation_id = new_conversation(client)
    for i in range(12):
        fake_adapter(chunks=("resposta " + "x" * 120,))
        send(client, conversation_id, f"pergunta {i} " + "y" * 120)

    adapter = fake_adapter(chunks=("ok",))
    events = sse_events(send(client, conversation_id, "ultima").text)
    meta = next(payload for name, payload in events if name == "meta")

    assert meta["context_trimmed"] > 0
    assert any("mensagens mais antigas foram omitidas" in m["content"] for m in adapter.received_messages)
    # A última pergunta nunca é cortada.
    assert adapter.received_messages[-1]["content"] == "ultima"


# ---------------------------------------------------------------- F3.5 regenerar


def test_regenerar_descarta_a_resposta_e_refaz(client, fake_adapter, db):
    fake_adapter(chunks=("primeira tentativa",))
    conversation_id = new_conversation(client)
    send(client, conversation_id, "oi")
    assistente = db.query(Message).filter_by(conversation_id=conversation_id, role="assistant").one()

    adapter = fake_adapter(chunks=("segunda tentativa",))
    resposta = client.post(f"/api/conversations/{conversation_id}/messages/{assistente.id}/regenerate")
    assert resposta.status_code == 200

    db.expire_all()
    mensagens = db.query(Message).filter_by(conversation_id=conversation_id).order_by(Message.id).all()
    assert [(m.role, m.content) for m in mensagens] == [
        ("user", "oi"),
        ("assistant", "segunda tentativa"),
    ]
    # O turno da usuária não foi duplicado.
    assert [m["role"] for m in adapter.received_messages].count("user") == 1


def test_nao_da_para_regenerar_uma_mensagem_da_usuaria(client, fake_adapter, db):
    fake_adapter()
    conversation_id = new_conversation(client)
    send(client, conversation_id, "oi")
    usuaria = db.query(Message).filter_by(conversation_id=conversation_id, role="user").one()

    resposta = client.post(f"/api/conversations/{conversation_id}/messages/{usuaria.id}/regenerate")
    assert resposta.status_code == 409


# ----------------------------------------------------------- erros como HTTP


def test_conversa_inexistente_vira_404_nao_stream_de_erro(client, fake_adapter):
    fake_adapter()
    assert send(client, 4242).status_code == 404


def test_conversa_arquivada_vira_409(client, fake_adapter):
    fake_adapter()
    conversation_id = new_conversation(client)
    client.delete(f"/api/conversations/{conversation_id}")
    assert send(client, conversation_id).status_code == 409


def test_provider_desativado_vira_409(client, fake_adapter, db):
    fake_adapter()
    ollama = next(p for p in client.get("/api/providers").json() if p["kind"] == "ollama")
    client.patch(f"/api/providers/{ollama['id']}", json={"is_enabled": False})
    conversation_id = new_conversation(client)
    assert send(client, conversation_id).status_code == 409


def test_fashion_tool_call_gera_objeto_sse_e_termina_a_resposta(client, monkeypatch, db):
    class ToolAdapter:
        capabilities = ProviderCapabilities(supports_tool_calls=True)
        last_usage = None

        def __init__(self):
            self.calls = 0
            self.last_tool_calls = []

        async def stream(self, messages, config) -> AsyncIterator[str]:
            self.calls += 1
            if self.calls == 1:
                assert config.tools
                self.last_tool_calls = [{"id": "call_wardrobe", "type": "function", "function": {"name": "get_wardrobe", "arguments": "{\"limit\": 2}"}}]
                if False:
                    yield ""
                return
            assert messages[-1]["role"] == "tool"
            self.last_tool_calls = []
            yield "Encontrei as peças cadastradas."

        async def list_models(self, base_url, api_key):
            return []

    # A habilitação pertence ao modelo da conversa.
    db.get(ModelConfig, 1).supports_tools = True
    db.commit()
    adapter = ToolAdapter()
    monkeypatch.setattr("app.services.chat.create_adapter", lambda _kind: adapter)
    client.post("/api/fashion/wardrobe", json={"name": "Blazer", "category": "outerwear"})
    conversation_id = new_conversation(client)

    events = sse_events(send(client, conversation_id, "o que eu tenho?").text)
    assert any(name == "ui_object" and payload["type"] == "wardrobe_view" for name, payload in events)
    assert events[-1][0] == "done"
    assert adapter.calls == 2
    # O card emitido no SSE também precisa sobreviver ao reload da conversa.
    history = client.get(f"/api/conversations/{conversation_id}")
    assert history.status_code == 200, history.text
    assert history.json()["messages"][-1]["ui_objects"][0]["type"] == "wardrobe_view"
