from app.services.llm.openai_compatible import OpenAICompatibleAdapter


class OllamaAdapter(OpenAICompatibleAdapter):
    def __init__(self) -> None:
        super().__init__(send_bearer_token=False)
