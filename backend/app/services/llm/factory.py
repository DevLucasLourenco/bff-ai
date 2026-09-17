"""Escolha de adapter por `provider.kind`. Sem fallback, por desenho (regra 1)."""

from app.services.llm.base import LLMAdapter
from app.services.llm.errors import UnsupportedProviderError
from app.services.llm.nvidia_nim import NvidiaNimAdapter
from app.services.llm.ollama import OllamaAdapter

# Registry no lugar do if/elif: adicionar um provider é uma linha aqui, e os
# Literal dos schemas derivam destas chaves em vez de repetirem a lista.
ADAPTERS: dict[str, type[LLMAdapter]] = {
    "ollama": OllamaAdapter,
    "nvidia_nim": NvidiaNimAdapter,
}

PROVIDER_KINDS = tuple(ADAPTERS)

__all__ = ["ADAPTERS", "PROVIDER_KINDS", "UnsupportedProviderError", "create_adapter", "capabilities_for"]


def create_adapter(kind: str) -> LLMAdapter:
    """Devolve exatamente o adapter pedido, ou levanta. Nunca substitui por outro."""
    try:
        return ADAPTERS[kind]()
    except KeyError as exc:
        raise UnsupportedProviderError(f"Provider sem adapter: {kind}") from exc


def capabilities_for(kind: str):
    """Capacidades declaradas sem instanciar o adapter (uso das rotas)."""
    try:
        return ADAPTERS[kind].capabilities
    except KeyError as exc:
        raise UnsupportedProviderError(f"Provider sem adapter: {kind}") from exc
