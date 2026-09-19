from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Protocol


@dataclass(frozen=True)
class ProviderCapabilities:
    """O que este provider aceita — declarado pelo adapter, não deduzido fora dele.

    Antes, o ChatService e a rota /models comparavam `provider.kind == "nvidia_nim"`
    para decidir max_tokens e reasoning_effort. Isso furava a regra 5 do README
    ("provider é adapter"): adicionar um terceiro provider obrigava a editar o
    chat e uma rota. Agora a regra mora aqui.
    """

    # NVIDIA NIM: False. Modelos de reasoning dividem o orçamento de tokens entre
    # o pensamento e a resposta visível, então um teto baixo consome o orçamento
    # antes de sair texto. Deixar o provider escolher o próprio default.
    honors_max_tokens: bool = True

    # Valor de `reasoning_effort` enviado quando o provider entende o campo.
    default_reasoning_effort: str | None = None

    # `stream_options: {"include_usage": true}` no payload. Só para provider onde
    # isso é verificado: pedir um campo que o servidor rejeita derruba o chat, e
    # a regra 1 ("sem fallback") proíbe tentar de novo sem o campo.
    supports_usage_in_stream: bool = False

    # Tool calls are opt-in: providers that have not been verified keep the
    # Fashion tools out of their payload altogether.
    supports_tool_calls: bool = False


@dataclass(frozen=True)
class ChatRuntimeConfig:
    base_url: str
    model_id: str
    api_key: str | None
    temperature: float
    max_tokens: int | None
    top_p: float
    reasoning_effort: str | None = None
    include_usage: bool = False
    tools: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class StreamUsage:
    prompt_tokens: int | None
    completion_tokens: int | None


class LLMAdapter(Protocol):
    capabilities: ProviderCapabilities

    async def stream(self, messages: list[dict[str, Any]], config: ChatRuntimeConfig) -> AsyncIterator[str]: ...

    async def list_models(self, base_url: str, api_key: str | None) -> list[str]: ...
