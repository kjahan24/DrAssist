"""`AIProviderFactory` / `EmbeddingProviderFactory` — configuration-driven
provider selection (the "Factory" half of `09_ai_gateway_and_storage.md`'s
"Strategy + Factory pattern for provider swapping").

Each factory holds a registry of `AIProviderType -> builder` — `create()`
looks up and invokes the builder for the requested type, lazily
constructing that one provider (so, e.g., asking for `MOCK` never
constructs an `OpenAIProvider`/imports the `openai` SDK). `container.py`
is the only place builders get registered, from `AISettings`; nothing
else in this module hardcodes which providers exist.
"""

from collections.abc import Callable

from app.modules.ai.application.ports import AIProviderPort, EmbeddingProviderPort
from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.exceptions import UnsupportedAIProviderError


class AIProviderFactory:
    def __init__(self) -> None:
        self._builders: dict[AIProviderType, Callable[[], AIProviderPort]] = {}

    def register(
        self, provider_type: AIProviderType, builder: Callable[[], AIProviderPort]
    ) -> None:
        self._builders[provider_type] = builder

    def create(self, provider_type: AIProviderType) -> AIProviderPort:
        builder = self._builders.get(provider_type)
        if builder is None:
            raise UnsupportedAIProviderError(provider_type.value)
        return builder()

    def available_providers(self) -> list[AIProviderType]:
        return list(self._builders.keys())


class EmbeddingProviderFactory:
    def __init__(self) -> None:
        self._builders: dict[AIProviderType, Callable[[], EmbeddingProviderPort]] = {}

    def register(
        self, provider_type: AIProviderType, builder: Callable[[], EmbeddingProviderPort]
    ) -> None:
        self._builders[provider_type] = builder

    def create(self, provider_type: AIProviderType) -> EmbeddingProviderPort:
        builder = self._builders.get(provider_type)
        if builder is None:
            raise UnsupportedAIProviderError(provider_type.value)
        return builder()

    def available_providers(self) -> list[AIProviderType]:
        return list(self._builders.keys())
