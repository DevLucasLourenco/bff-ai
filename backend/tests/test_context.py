"""ContextBuilder: puro, sem banco e sem rede (F4.1/F4.2)."""

from app.services.context import (
    MEMORY_PREAMBLE,
    TRIM_NOTICE,
    ContextMessage,
    build_messages,
    estimate_tokens,
    prompt_budget,
)


def historico(n: int, tamanho: int = 100) -> list[ContextMessage]:
    return [
        ContextMessage("user" if i % 2 == 0 else "assistant", f"m{i} " + "x" * tamanho)
        for i in range(n)
    ]


def test_ordem_persona_memorias_historico():
    contexto = build_messages(
        system_prompt="Você é a Bestie.",
        memories=[("pref", "gosta de café")],
        history=[ContextMessage("user", "oi")],
    )
    papeis = [m["role"] for m in contexto.messages]
    assert papeis == ["system", "system", "user"]
    assert contexto.messages[0]["content"] == "Você é a Bestie."
    assert contexto.messages[1]["content"].startswith(MEMORY_PREAMBLE)


def test_sem_memorias_nao_cria_bloco_vazio():
    contexto = build_messages(system_prompt="p", history=[ContextMessage("user", "oi")])
    assert [m["role"] for m in contexto.messages] == ["system", "user"]
    assert contexto.used_memories == 0


def test_janela_desconhecida_nao_trunca():
    contexto = build_messages(system_prompt="p", history=historico(200), context_window=0)
    assert contexto.dropped_messages == 0
    assert contexto.budget_tokens is None
    assert len(contexto.messages) == 201


def test_orcamento_reserva_espaco_para_a_resposta():
    # 25% da janela fica para a resposta.
    assert prompt_budget(1000) == 750
    assert prompt_budget(0) is None


def test_trunca_as_mais_antigas_e_avisa():
    contexto = build_messages(system_prompt="p", history=historico(50), context_window=800)

    assert contexto.dropped_messages > 0
    assert any(m["content"] == TRIM_NOTICE for m in contexto.messages)
    # O que sobra é o fim da conversa, não o começo.
    assert contexto.messages[-1]["content"].startswith("m49")
    assert contexto.estimated_prompt_tokens <= prompt_budget(800)


def test_ultima_mensagem_nunca_e_cortada():
    gigante = [ContextMessage("user", "z" * 100_000)]
    contexto = build_messages(system_prompt="p", history=gigante, context_window=100)
    # Sem ela não há pergunta a responder; o provider devolve ContextOverflow,
    # que é um erro tipado e explicável.
    assert contexto.messages[-1]["content"] == gigante[0].content


def test_teto_de_memorias_por_turno():
    memorias = [("cat", f"memoria {i}") for i in range(200)]
    contexto = build_messages(system_prompt="p", memories=memorias, history=[], memory_limit=10)
    assert contexto.used_memories == 10
    assert "memoria 9" in contexto.messages[1]["content"]
    assert "memoria 10" not in contexto.messages[1]["content"]


def test_estimativa_de_tokens_e_monotonica():
    assert estimate_tokens("") >= 1
    assert estimate_tokens("a" * 400) > estimate_tokens("a" * 40)
