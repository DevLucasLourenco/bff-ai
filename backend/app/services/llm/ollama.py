from app.services.llm.base import ProviderCapabilities
from app.services.llm.openai_compatible import OpenAICompatibleAdapter


class OllamaAdapter(OpenAICompatibleAdapter):
    # Ollama local honra max_tokens e não tem reasoning_effort.
    # supports_usage_in_stream fica False: a versão do Ollama varia por máquina e
    # um servidor antigo pode rejeitar `stream_options`, o que derrubaria o chat
    # inteiro. Ligar é trocar este campo para True depois de verificar na sua versão.
    capabilities = ProviderCapabilities(
        honors_max_tokens=True,
        default_reasoning_effort=None,
        supports_usage_in_stream=False,
    )

    def __init__(self) -> None:
        super().__init__(send_bearer_token=False)
