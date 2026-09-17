from app.services.llm.base import LLMAdapter
from app.services.llm.nvidia_nim import NvidiaNimAdapter
from app.services.llm.ollama import OllamaAdapter


class UnsupportedProviderError(ValueError):
    pass


def create_adapter(kind: str) -> LLMAdapter:
    # Deliberately no fallback. One provider kind maps to exactly one adapter.
    if kind == "ollama":
        return OllamaAdapter()
    if kind == "nvidia_nim":
        return NvidiaNimAdapter()
    raise UnsupportedProviderError(f"Unsupported provider kind: {kind}")
