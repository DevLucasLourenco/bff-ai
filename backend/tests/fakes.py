"""Adapter de LLM falso, determinístico e sem rede (F6.1)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.services.llm.base import ChatRuntimeConfig, ProviderCapabilities

DEFAULT_CHUNKS = ("Oi", ", ", "tudo", " bem", "?")


class FakeAdapter:
    """Emite chunks previsíveis e registra o que recebeu.

    `fail_after=N` levanta depois de emitir N chunks — é assim que os testes
    reproduzem "provider caiu no meio da resposta" sem derrubar nada de verdade.
    """

    def __init__(
        self,
        *,
        chunks: tuple[str, ...] = DEFAULT_CHUNKS,
        fail_after: int | None = None,
        error: Exception | None = None,
        models: tuple[str, ...] = ("fake-model-a", "fake-model-b"),
        capabilities: ProviderCapabilities | None = None,
        usage: dict[str, int] | None = None,
        delay: float = 0.0,
    ) -> None:
        self.chunks = chunks
        self.fail_after = fail_after
        self.error = error or RuntimeError("provider caiu no meio da resposta")
        self.models = models
        self.capabilities = capabilities or ProviderCapabilities()
        self._usage = usage
        # Espera antes de cada chunk: simula um modelo que demora a responder.
        self.delay = delay
        # Gravado para os testes inspecionarem a composição do prompt.
        self.received_messages: list[dict[str, str]] = []
        self.received_config: ChatRuntimeConfig | None = None
        self.last_usage: dict[str, int] | None = None

    async def stream(self, messages: list[dict[str, str]], config: ChatRuntimeConfig) -> AsyncIterator[str]:
        self.received_messages = list(messages)
        self.received_config = config
        self.last_usage = None
        for index, chunk in enumerate(self.chunks):
            if self.fail_after is not None and index >= self.fail_after:
                raise self.error
            if self.delay:
                await asyncio.sleep(self.delay)
            yield chunk
        self.last_usage = self._usage

    async def list_models(self, base_url: str, api_key: str | None) -> list[str]:
        return list(self.models)
