"""O adapter OpenAI-compatível contra um transporte falso — sem rede.

O teste de stream truncado existe por causa de um defeito encontrado rodando o
app de verdade: quando o provider fecha a conexão no meio, `aiter_lines` apenas
termina, sem levantar. O backend gravava a resposta truncada como `complete` —
corrupção silenciosa exatamente do tipo que a Fase 3 existe para impedir.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.services.llm.base import ChatRuntimeConfig
from app.services.llm.errors import (
    ContextOverflow,
    ModelNotFound,
    ProviderAuthError,
    ProviderResponseError,
    ProviderUnreachable,
)
from app.services.llm.ollama import OllamaAdapter

CONFIG = ChatRuntimeConfig(
    base_url="http://provider.test/v1",
    model_id="modelo",
    api_key=None,
    temperature=0.7,
    max_tokens=None,
    top_p=0.9,
)


def sse(*frames: str) -> bytes:
    return "".join(f"data: {frame}\n\n" for frame in frames).encode()


def delta(text: str) -> str:
    return json.dumps({"choices": [{"delta": {"content": text}}]})


def adapter_com(handler) -> OllamaAdapter:
    adapter = OllamaAdapter()
    transport = httpx.MockTransport(handler)
    adapter._client = lambda timeout: httpx.AsyncClient(transport=transport, timeout=timeout)  # type: ignore[method-assign]
    return adapter


async def coletar(adapter, config=CONFIG) -> list[str]:
    return [chunk async for chunk in adapter.stream([{"role": "user", "content": "oi"}], config)]


@pytest.mark.asyncio
async def test_stream_completo_com_done():
    adapter = adapter_com(lambda _r: httpx.Response(200, content=sse(delta("oi"), delta(" você"), "[DONE]")))
    assert await coletar(adapter) == ["oi", " você"]


@pytest.mark.asyncio
async def test_finish_reason_tambem_encerra():
    frames = sse(delta("oi"), json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}))
    adapter = adapter_com(lambda _r: httpx.Response(200, content=frames))
    assert await coletar(adapter) == ["oi"]


@pytest.mark.asyncio
async def test_stream_truncado_vira_erro_em_vez_de_resposta_completa():
    # Sem [DONE] e sem finish_reason: o provider desistiu no meio.
    adapter = adapter_com(lambda _r: httpx.Response(200, content=sse(delta("come"), delta("ço"))))
    with pytest.raises(ProviderResponseError, match="encerrou a conexão"):
        await coletar(adapter)


@pytest.mark.asyncio
async def test_usage_e_capturado_quando_o_provider_manda():
    frames = sse(delta("oi"), json.dumps({"choices": [], "usage": {"prompt_tokens": 12, "completion_tokens": 3}}), "[DONE]")
    adapter = adapter_com(lambda _r: httpx.Response(200, content=frames))
    await coletar(adapter)
    assert adapter.last_usage == {"prompt_tokens": 12, "completion_tokens": 3}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "corpo", "esperado"),
    [
        (401, "invalid api key", ProviderAuthError),
        (403, "forbidden", ProviderAuthError),
        (404, "model not found", ModelNotFound),
        (400, "maximum context length exceeded", ContextOverflow),
        (500, "boom", ProviderResponseError),
    ],
)
async def test_status_http_vira_erro_tipado(status, corpo, esperado):
    adapter = adapter_com(lambda _r: httpx.Response(status, text=corpo))
    with pytest.raises(esperado):
        await coletar(adapter)


@pytest.mark.asyncio
async def test_provider_inalcancavel():
    def recusa(_request):
        raise httpx.ConnectError("connection refused")

    adapter = adapter_com(recusa)
    with pytest.raises(ProviderUnreachable):
        await coletar(adapter)


@pytest.mark.asyncio
async def test_a_api_key_nunca_aparece_no_erro():
    segredo = "nvapi-chave-secreta"
    config = ChatRuntimeConfig(**{**CONFIG.__dict__, "api_key": segredo})
    adapter = adapter_com(lambda _r: httpx.Response(401, text="invalid api key"))
    with pytest.raises(ProviderAuthError) as exc:
        await coletar(adapter, config)
    assert segredo not in str(exc.value)
    assert segredo not in (exc.value.provider_detail or "")


@pytest.mark.asyncio
async def test_stream_options_so_vai_quando_a_capacidade_permite():
    capturado: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado.update(json.loads(request.content))
        return httpx.Response(200, content=sse(delta("ok"), "[DONE]"))

    adapter = adapter_com(handler)
    await coletar(adapter)
    assert "stream_options" not in capturado  # Ollama: supports_usage_in_stream=False

    adapter = adapter_com(handler)
    await coletar(adapter, ChatRuntimeConfig(**{**CONFIG.__dict__, "include_usage": True}))
    assert capturado["stream_options"] == {"include_usage": True}
