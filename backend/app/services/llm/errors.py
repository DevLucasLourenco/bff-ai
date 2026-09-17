"""Exceções de domínio para falhas de provider (F5.1).

Antes, qualquer falha virava `RuntimeError(f"LLM returned HTTP {status}: {body[:800]}")`
e esse texto ia cru para o evento SSE `error` e para a tela. A usuária via um JSON
da NVIDIA, e o app não conseguia distinguir "chave recusada" de "modelo inexistente"
de "Ollama desligado" para sugerir a ação certa.

Cada exceção carrega um `code` estável (contrato com o frontend) e um
`provider_detail` opcional, que é o texto do provider truncado — útil para
diagnóstico local, mas separado da mensagem que a usuária lê.
"""

from __future__ import annotations

DETAIL_LIMIT = 500


class LLMError(RuntimeError):
    code = "llm_error"
    http_status = 502

    def __init__(self, message: str, *, provider_detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.provider_detail = (provider_detail or "")[:DETAIL_LIMIT] or None

    def as_payload(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "provider_detail": self.provider_detail}


class ProviderUnreachable(LLMError):
    code = "provider_unreachable"
    http_status = 503


class ProviderAuthError(LLMError):
    code = "provider_auth"
    http_status = 502


class ModelNotFound(LLMError):
    code = "model_not_found"
    http_status = 502


class ContextOverflow(LLMError):
    code = "context_overflow"
    http_status = 502


class ProviderResponseError(LLMError):
    code = "provider_error"
    http_status = 502


class UnsupportedProviderError(LLMError):
    """Provider sem adapter. Nunca vira fallback — é erro terminal (regra 1)."""

    code = "unsupported_provider"
    http_status = 400
