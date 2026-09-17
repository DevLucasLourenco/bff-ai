"""Tradução de linhas do banco para `ChatRuntimeConfig`, guiada por capacidades.

Este é o único lugar que decide max_tokens/reasoning_effort efetivos. Antes a
decisão estava duplicada no ChatService e na rota /models, comparando strings de
provider — o que obrigava a editar chat e rota a cada provider novo.
"""

from __future__ import annotations

from app.services.llm.base import ChatRuntimeConfig
from app.services.llm.factory import capabilities_for

# 0 é o sentinela histórico no SQLite para "o provider decide".
PROVIDER_MANAGED = 0


def effective_max_tokens(provider_kind: str, stored_max_tokens: int) -> int | None:
    if stored_max_tokens <= PROVIDER_MANAGED:
        return None
    if not capabilities_for(provider_kind).honors_max_tokens:
        return None
    return stored_max_tokens


def build_runtime_config(
    *,
    provider_kind: str,
    base_url: str,
    api_key: str | None,
    model_id: str,
    stored_max_tokens: int,
    temperature: float,
    top_p: float,
) -> ChatRuntimeConfig:
    capabilities = capabilities_for(provider_kind)
    return ChatRuntimeConfig(
        base_url=base_url,
        model_id=model_id,
        api_key=api_key,
        temperature=temperature,
        max_tokens=effective_max_tokens(provider_kind, stored_max_tokens),
        top_p=top_p,
        reasoning_effort=capabilities.default_reasoning_effort,
        include_usage=capabilities.supports_usage_in_stream,
    )
