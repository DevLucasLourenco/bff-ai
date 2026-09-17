from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Protocol


@dataclass(frozen=True)
class ChatRuntimeConfig:
    base_url: str
    model_id: str
    api_key: str | None
    temperature: float
    max_tokens: int | None
    top_p: float
    reasoning_effort: str | None = None


class LLMAdapter(Protocol):
    async def stream(self, messages: list[dict[str, str]], config: ChatRuntimeConfig) -> AsyncIterator[str]: ...

    async def list_models(self, base_url: str, api_key: str | None) -> list[str]: ...
