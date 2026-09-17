from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from app.services.llm.base import ChatRuntimeConfig


class OpenAICompatibleAdapter:
    def __init__(self, *, send_bearer_token: bool) -> None:
        self.send_bearer_token = send_bearer_token

    def _headers(self, api_key: str | None) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.send_bearer_token and api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    @staticmethod
    def _endpoint(base_url: str, path: str) -> str:
        return f"{base_url.rstrip('/')}/{path.lstrip('/')}"

    async def stream(self, messages: list[dict[str, str]], config: ChatRuntimeConfig) -> AsyncIterator[str]:
        payload = {
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
        timeout = httpx.Timeout(120.0, connect=15.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                self._endpoint(config.base_url, "chat/completions"),
                headers=self._headers(config.api_key),
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    body = (await response.aread()).decode(errors="replace")
                    raise RuntimeError(f"LLM returned HTTP {response.status_code}: {body[:800]}")
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        event = json.loads(data)
                        delta = event.get("choices", [{}])[0].get("delta", {}).get("content")
                    except (json.JSONDecodeError, IndexError, TypeError):
                        continue
                    if delta:
                        yield delta

    async def list_models(self, base_url: str, api_key: str | None) -> list[str]:
        timeout = httpx.Timeout(20.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                self._endpoint(base_url, "models"),
                headers=self._headers(api_key),
            )
            response.raise_for_status()
            payload = response.json()
            return sorted(item["id"] for item in payload.get("data", []) if item.get("id"))
