"""Montagem do prompt — pura, sem banco e sem rede (F4.1).

Estava embutida no meio de `ChatService.stream_message`: persona, memórias e
histórico concatenados inline. É a parte do sistema que mais vai mudar (memórias,
anexos, ferramentas) e era a única sem camada própria nem forma de testar sem
simular um stream inteiro.
"""

from __future__ import annotations

from dataclasses import dataclass

MEMORY_PREAMBLE = (
    "Memórias persistentes fornecidas explicitamente pela usuária. "
    "Use-as apenas quando forem relevantes e não invente detalhes além delas:"
)

TRIM_NOTICE = (
    "Aviso de contexto: esta conversa é longa e as mensagens mais antigas foram "
    "omitidas para caber na janela do modelo. Não afirme lembrar do que não está aqui."
)

# Fração da janela reservada para a resposta. O restante é o teto do prompt.
RESPONSE_RESERVE_RATIO = 0.25

# Teto de memórias injetadas por turno, independente da janela do modelo.
DEFAULT_MEMORY_LIMIT = 40


@dataclass(frozen=True)
class ContextMessage:
    role: str
    content: str

    def as_payload(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class BuiltContext:
    messages: list[dict[str, str]]
    dropped_messages: int = 0
    estimated_prompt_tokens: int = 0
    used_memories: int = 0
    budget_tokens: int | None = None

    @property
    def was_trimmed(self) -> bool:
        return self.dropped_messages > 0


def estimate_tokens(text: str) -> int:
    """Estimativa grosseira (~4 caracteres por token).

    Deliberadamente sem tokenizer: cada modelo usa o seu, e carregar um por
    provider custaria mais do que a precisão vale aqui. A estimativa só decide
    quanto histórico cortar, e o corte é conservador por causa da reserva.
    """
    return max(1, len(text) // 4)


def prompt_budget(context_window: int) -> int | None:
    """Teto de tokens do prompt, ou None quando a janela é desconhecida."""
    if context_window <= 0:
        return None
    return max(1, int(context_window * (1 - RESPONSE_RESERVE_RATIO)))


def format_memories(memories: list[tuple[str, str]]) -> str:
    lines = "\n".join(f"- [{category}] {content}" for category, content in memories)
    return f"{MEMORY_PREAMBLE}\n{lines}"


def build_messages(
    *,
    system_prompt: str,
    history: list[ContextMessage],
    memories: list[tuple[str, str]] | None = None,
    context_window: int = 0,
    memory_limit: int = DEFAULT_MEMORY_LIMIT,
) -> BuiltContext:
    """Monta o payload de mensagens respeitando o orçamento de tokens.

    Ordem: system prompt da persona → bloco de memórias → histórico. O que é
    cortado quando falta espaço é sempre o histórico **mais antigo**: persona e
    memórias são a identidade da conversa e nunca saem.
    """
    capped_memories = (memories or [])[:memory_limit]
    head: list[ContextMessage] = [ContextMessage("system", system_prompt)]
    if capped_memories:
        head.append(ContextMessage("system", format_memories(capped_memories)))

    budget = prompt_budget(context_window)
    if budget is None:
        messages = head + history
        return BuiltContext(
            messages=[m.as_payload() for m in messages],
            dropped_messages=0,
            estimated_prompt_tokens=sum(estimate_tokens(m.content) for m in messages),
            used_memories=len(capped_memories),
            budget_tokens=None,
        )

    fixed_cost = sum(estimate_tokens(m.content) for m in head) + estimate_tokens(TRIM_NOTICE)
    remaining = budget - fixed_cost

    # Percorre o histórico do mais recente para o mais antigo, mantendo o que couber.
    kept_reversed: list[ContextMessage] = []
    for message in reversed(history):
        cost = estimate_tokens(message.content)
        if remaining - cost < 0:
            break
        remaining -= cost
        kept_reversed.append(message)
    kept = list(reversed(kept_reversed))
    if not kept and history:
        # A última mensagem sozinha já estoura o orçamento. Manda mesmo assim: sem
        # ela não há pergunta a responder, e o provider devolve ContextOverflow —
        # um erro tipado e explicável, melhor que um prompt sem conteúdo.
        kept = [history[-1]]
    dropped = len(history) - len(kept)

    messages = list(head)
    if dropped:
        messages.append(ContextMessage("system", TRIM_NOTICE))
    messages.extend(kept)
    return BuiltContext(
        messages=[m.as_payload() for m in messages],
        dropped_messages=dropped,
        estimated_prompt_tokens=sum(estimate_tokens(m.content) for m in messages),
        used_memories=len(capped_memories),
        budget_tokens=budget,
    )
