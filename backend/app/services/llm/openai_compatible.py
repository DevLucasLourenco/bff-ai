from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from app.services.llm.base import ChatRuntimeConfig, ProviderCapabilities
from app.services.llm.errors import (
    ContextOverflow,
    ModelNotFound,
    ProviderAuthError,
    ProviderResponseError,
    ProviderUnreachable,
)

# Pistas no corpo da resposta que identificam estouro de contexto. Usadas só para
# escolher a mensagem certa; nunca para decidir tentar de novo.
_CONTEXT_HINTS = ("context length", "context_length", "too many tokens", "maximum context", "reduce the length")

# Assinatura do 404 da NVIDIA quando o modelo existe no catálogo mas a conta não
# pode invocá-lo: `Function '<uuid>': Not found for account '<id>'`.
_SEM_ACESSO_NA_CONTA = "not found for account"


class OpenAICompatibleAdapter:
    capabilities = ProviderCapabilities()

    def __init__(self, *, send_bearer_token: bool) -> None:
        self.send_bearer_token = send_bearer_token
        # Preenchido ao fim de um stream quando o provider devolve `usage`.
        # Seguro porque create_adapter() devolve uma instância por requisição.
        self.last_usage: dict[str, int] | None = None
        self.last_tool_calls: list[dict[str, Any]] = []

    def _headers(self, api_key: str | None) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.send_bearer_token and api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    @staticmethod
    def _endpoint(base_url: str, path: str) -> str:
        return f"{base_url.rstrip('/')}/{path.lstrip('/')}"

    def _build_payload(self, messages: list[dict[str, Any]], config: ChatRuntimeConfig) -> dict:
        payload: dict = {
            "model": config.model_id,
            "messages": messages,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": True,
        }
        if config.max_tokens is not None:
            payload["max_tokens"] = config.max_tokens
        if config.reasoning_effort is not None:
            payload["reasoning_effort"] = config.reasoning_effort
        if config.include_usage:
            payload["stream_options"] = {"include_usage": True}
        if config.tools:
            payload["tools"] = config.tools
            payload["tool_choice"] = config.tool_choice
        return payload

    def _raise_for_status(self, status: int, body: str) -> None:
        lowered = body.lower()
        if status in (401, 403):
            raise ProviderAuthError(
                "O provider recusou a credencial. Confira a API key em Configurações → LLM.",
                provider_detail=body,
            )
        if status == 404:
            # A NVIDIA lista no catálogo de /v1/models muitos modelos que a conta
            # não pode invocar: "listado" e "executável" são coisas diferentes lá.
            # Mandar "consulte os modelos disponíveis" nesse caso é enganoso,
            # porque o modelo *está* na lista.
            if _SEM_ACESSO_NA_CONTA in lowered:
                raise ModelNotFound(
                    "Esse modelo aparece no catálogo do provider, mas a sua conta não tem acesso "
                    "para executá-lo. Escolha outro modelo em Configurações → LLM.",
                    provider_detail=body,
                )
            raise ModelNotFound(
                "O provider não encontrou esse modelo. Consulte os modelos disponíveis e escolha outro.",
                provider_detail=body,
            )
        if status in (400, 413, 422) and any(hint in lowered for hint in _CONTEXT_HINTS):
            raise ContextOverflow(
                "A conversa ficou maior que a janela de contexto do modelo.",
                provider_detail=body,
            )
        raise ProviderResponseError(
            f"O provider respondeu com erro HTTP {status}.",
            provider_detail=body,
        )

    def _client(self, timeout: httpx.Timeout) -> httpx.AsyncClient:
        # Isolado para os testes poderem injetar um transporte falso.
        return httpx.AsyncClient(timeout=timeout)

    async def stream(self, messages: list[dict[str, Any]], config: ChatRuntimeConfig) -> AsyncIterator[str]:
        self.last_usage = None
        self.last_tool_calls = []
        tool_calls: dict[int, dict[str, Any]] = {}
        payload = self._build_payload(messages, config)
        timeout = httpx.Timeout(120.0, connect=15.0)
        # O protocolo sinaliza fim com `[DONE]` (ou um finish_reason). Sem essa
        # marca, um provider que derruba a conexão no meio é indistinguível de
        # uma resposta que acabou — e a resposta truncada seria salva como
        # completa, que é justamente a corrupção silenciosa que o F3.1 combate.
        saw_terminator = False
        try:
            async with self._client(timeout) as client:
                async with client.stream(
                    "POST",
                    self._endpoint(config.base_url, "chat/completions"),
                    headers=self._headers(config.api_key),
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        body = (await response.aread()).decode(errors="replace")
                        self._raise_for_status(response.status_code, body)
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            saw_terminator = True
                            break
                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        # O frame final de usage vem com choices vazio.
                        usage = event.get("usage")
                        if isinstance(usage, dict):
                            self.last_usage = {
                                "prompt_tokens": usage.get("prompt_tokens"),
                                "completion_tokens": usage.get("completion_tokens"),
                            }
                        choices = event.get("choices") or []
                        if choices and choices[0].get("finish_reason"):
                            saw_terminator = True
                        try:
                            choice = choices[0] if choices else {}
                            delta_data = choice.get("delta", {})
                            delta = delta_data.get("content")
                        except (IndexError, TypeError, AttributeError):
                            continue
                        for fragment in delta_data.get("tool_calls", []) or []:
                            if not isinstance(fragment, dict):
                                continue
                            index = int(fragment.get("index", 0))
                            call = tool_calls.setdefault(index, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                            if fragment.get("id"):
                                call["id"] = fragment["id"]
                            function = fragment.get("function") or {}
                            if function.get("name"):
                                call["function"]["name"] += function["name"]
                            if function.get("arguments"):
                                call["function"]["arguments"] += function["arguments"]
                        if delta:
                            yield delta
        except httpx.HTTPError as exc:
            # Inclui timeout, DNS e conexão recusada — o caso "Ollama desligado".
            raise ProviderUnreachable(
                f"Não foi possível falar com o provider em {config.base_url}.",
                provider_detail=str(exc),
            ) from exc

        if not saw_terminator:
            raise ProviderResponseError(
                "O provider encerrou a conexão antes de terminar a resposta.",
                provider_detail="stream sem [DONE] nem finish_reason",
            )
        self.last_tool_calls = [call for _, call in sorted(tool_calls.items()) if call["id"] and call["function"]["name"]]

    async def list_models(self, base_url: str, api_key: str | None) -> list[str]:
        timeout = httpx.Timeout(20.0, connect=5.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    self._endpoint(base_url, "models"),
                    headers=self._headers(api_key),
                )
                if response.status_code >= 400:
                    self._raise_for_status(response.status_code, response.text)
                payload = response.json()
        except httpx.HTTPError as exc:
            raise ProviderUnreachable(
                f"Não foi possível falar com o provider em {base_url}.",
                provider_detail=str(exc),
            ) from exc
        return sorted(item["id"] for item in payload.get("data", []) if item.get("id"))
