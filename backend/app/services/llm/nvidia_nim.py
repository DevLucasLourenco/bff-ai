from app.services.llm.base import ProviderCapabilities
from app.services.llm.openai_compatible import OpenAICompatibleAdapter


class NvidiaNimAdapter(OpenAICompatibleAdapter):
    # honors_max_tokens=False: modelos de reasoning do NIM dividem o orçamento de
    # tokens entre o pensamento e a resposta visível, então o teto de 2048 do
    # ModelConfig consumia o orçamento antes de sair texto visível.
    capabilities = ProviderCapabilities(
        honors_max_tokens=False,
        default_reasoning_effort="none",
        supports_usage_in_stream=True,
    )

    def __init__(self) -> None:
        super().__init__(send_bearer_token=True)
