import pytest
from app.services.llm.factory import UnsupportedProviderError, create_adapter
from app.services.llm.nvidia_nim import NvidiaNimAdapter
from app.services.llm.ollama import OllamaAdapter


def test_factory_maps_exact_provider_without_fallback():
    assert isinstance(create_adapter("ollama"), OllamaAdapter)
    assert isinstance(create_adapter("nvidia_nim"), NvidiaNimAdapter)
    with pytest.raises(UnsupportedProviderError):
        create_adapter("unknown")
