"""Unit tests for `resolve_default_ai_model`/`resolve_default_embedding_model`
— using a duck-typed stand-in for `app.core.config.Settings` (see
`app.modules.icd10_ai`'s own identical test for why: constructing the
real `Settings` is unnecessary, and mutating the process-wide
`get_settings()` singleton to test each provider branch would leak state
into other tests)."""

from types import SimpleNamespace

from app.modules.ai.public.dto import AIProviderType
from app.modules.community_ai.infrastructure.provider_selection import (
    resolve_default_ai_model,
    resolve_default_embedding_model,
)


def _settings(
    *,
    default_provider: str = "mock",
    default_embedding_provider: str = "mock",
    openai_model: str = "gpt-4o-mini",
    openai_embedding_model: str = "text-embedding-3-small",
    gemini_model: str = "gemini-2.5-pro",
    gemini_embedding_model: str = "text-embedding-004",
    anthropic_model: str = "claude-3-5-sonnet-latest",
    ollama_model: str = "llama3.1",
) -> object:
    return SimpleNamespace(
        ai=SimpleNamespace(
            default_provider=default_provider,
            default_embedding_provider=default_embedding_provider,
            openai_model=openai_model,
            openai_embedding_model=openai_embedding_model,
            gemini_embedding_model=gemini_embedding_model,
            anthropic_model=anthropic_model,
            ollama_model=ollama_model,
        ),
        gemini=SimpleNamespace(model=gemini_model),
    )


class TestResolveDefaultAIModel:
    def test_openai_provider_uses_openai_model_setting(self) -> None:
        model = resolve_default_ai_model(_settings(default_provider="openai"))  # type: ignore[arg-type]
        assert model.provider is AIProviderType.OPENAI
        assert model.name == "gpt-4o-mini"

    def test_gemini_provider_uses_the_shared_gemini_settings_group(self) -> None:
        model = resolve_default_ai_model(_settings(default_provider="gemini"))  # type: ignore[arg-type]
        assert model.provider is AIProviderType.GEMINI
        assert model.name == "gemini-2.5-pro"

    def test_claude_provider_uses_anthropic_model_setting(self) -> None:
        model = resolve_default_ai_model(_settings(default_provider="claude"))  # type: ignore[arg-type]
        assert model.provider is AIProviderType.CLAUDE
        assert model.name == "claude-3-5-sonnet-latest"

    def test_ollama_provider_uses_ollama_model_setting(self) -> None:
        model = resolve_default_ai_model(_settings(default_provider="ollama"))  # type: ignore[arg-type]
        assert model.provider is AIProviderType.OLLAMA
        assert model.name == "llama3.1"

    def test_mock_provider_uses_a_fixed_model_name(self) -> None:
        model = resolve_default_ai_model(_settings(default_provider="mock"))  # type: ignore[arg-type]
        assert model.provider is AIProviderType.MOCK
        assert model.name == "mock-model"


class TestResolveDefaultEmbeddingModel:
    def test_openai_embedding_provider(self) -> None:
        model = resolve_default_embedding_model(
            _settings(default_embedding_provider="openai")  # type: ignore[arg-type]
        )
        assert model.provider is AIProviderType.OPENAI
        assert model.name == "text-embedding-3-small"
        assert model.supports_embeddings is True

    def test_gemini_embedding_provider(self) -> None:
        model = resolve_default_embedding_model(
            _settings(default_embedding_provider="gemini")  # type: ignore[arg-type]
        )
        assert model.provider is AIProviderType.GEMINI
        assert model.name == "text-embedding-004"

    def test_mock_embedding_provider_uses_a_fixed_model_name(self) -> None:
        model = resolve_default_embedding_model(
            _settings(default_embedding_provider="mock")  # type: ignore[arg-type]
        )
        assert model.provider is AIProviderType.MOCK
        assert model.name == "mock-model"
