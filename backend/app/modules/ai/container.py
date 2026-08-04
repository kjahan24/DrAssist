"""Module composition root for the AI Foundation.

Scope note — this task builds the AI module's **Foundation** layer only:
a provider-agnostic `AIProviderPort`/`EmbeddingProviderPort` abstraction
over OpenAI/Gemini/Claude/Ollama/Mock, a versioned prompt system, and the
cross-cutting resilience/cost/audit/usage plumbing every provider call
runs through (`infrastructure/providers/resilient_provider.py`). It does
**not** build any clinical AI feature (Clinical Notes AI, SOAP AI, ICD
coding, prescription assist, differential diagnosis, voice, or lab
interpretation — each is a separate future module consuming
`public/interfaces.py::AIGatewayPort`), the persisted `AiSession`/
`ConversationTranscript` aggregate or async Celery orchestration described
for the full AI Gateway in `docs/backend-architecture
/09_ai_gateway_and_storage.md`/`03_module_architecture.md #10` (no
`ai_sessions` table exists yet), or a durable prompt-template store (
`infrastructure/prompts/in_memory_repository.py` is process-lifetime only
— see that file's own docstring for why that's an acceptable scope for a
Foundation-only task).

Unlike every DB-backed module's `container.py` (`build_<module>_facade
(session)`, constructed fresh per request because it wraps a request-scoped
`AsyncSession`), this module owns no database session or per-request
state at all — every provider/factory/registry built here is genuinely
process-lifetime, so each is exposed as an `lru_cache`d singleton, the same
pattern `app.core.container.get_event_bus` and the pre-existing
`app.infrastructure.ai.gemini_client.get_gemini_client` already establish.
"""

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.modules.ai.application.ports import (
    AIAuditLoggerPort,
    AIProviderPort,
    CostCalculatorPort,
    EmbeddingProviderPort,
)
from app.modules.ai.application.services.token_usage_collector import TokenUsageCollector
from app.modules.ai.application.use_cases.generate_chat_completion import GenerateChatCompletion
from app.modules.ai.application.use_cases.generate_embedding import GenerateEmbedding
from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.infrastructure.embeddings.gemini_embedding_provider import (
    GeminiEmbeddingProvider,
)
from app.modules.ai.infrastructure.embeddings.mock_embedding_provider import MockEmbeddingProvider
from app.modules.ai.infrastructure.embeddings.openai_embedding_provider import (
    OpenAIEmbeddingProvider,
)
from app.modules.ai.infrastructure.llm.claude_provider import ClaudeProvider
from app.modules.ai.infrastructure.llm.gemini_provider import GeminiChatProvider
from app.modules.ai.infrastructure.llm.mock_provider import MockAIProvider
from app.modules.ai.infrastructure.llm.ollama_provider import OllamaProvider
from app.modules.ai.infrastructure.llm.openai_provider import OpenAIProvider
from app.modules.ai.infrastructure.prompts.in_memory_repository import (
    InMemoryPromptTemplateRepository,
)
from app.modules.ai.infrastructure.prompts.registry import PromptRegistry
from app.modules.ai.infrastructure.providers.audit_logger import StructlogAIAuditLogger
from app.modules.ai.infrastructure.providers.cost_calculator import StaticTablePricingCostCalculator
from app.modules.ai.infrastructure.providers.factory import (
    AIProviderFactory,
    EmbeddingProviderFactory,
)
from app.modules.ai.infrastructure.providers.resilient_provider import (
    ResilientAIProvider,
    ResilientEmbeddingProvider,
)
from app.modules.ai.infrastructure.providers.retry import RetryPolicy
from app.modules.ai.public.facade import AIGatewayFacade


@lru_cache
def get_token_usage_collector() -> TokenUsageCollector:
    return TokenUsageCollector()


@lru_cache
def get_ai_audit_logger() -> AIAuditLoggerPort:
    return StructlogAIAuditLogger()


@lru_cache
def get_cost_calculator() -> CostCalculatorPort:
    return StaticTablePricingCostCalculator()


@lru_cache
def get_prompt_registry() -> PromptRegistry:
    """Starts empty — no clinical prompt templates are registered here
    per this file's own scope note; a future clinical module registers
    its own templates via `PromptRegistry.register()` at its own
    `container.py` import time."""
    return PromptRegistry(repository=InMemoryPromptTemplateRepository())


def _retry_policy(settings: Settings) -> RetryPolicy:
    return RetryPolicy(
        max_attempts=settings.ai.max_retry_attempts,
        initial_backoff_seconds=settings.ai.retry_initial_backoff_seconds,
        max_backoff_seconds=settings.ai.retry_max_backoff_seconds,
    )


def _wrap_chat_provider(inner: AIProviderPort, settings: Settings) -> ResilientAIProvider:
    return ResilientAIProvider(
        inner=inner,
        retry_policy=_retry_policy(settings),
        timeout_seconds=settings.ai.request_timeout_seconds,
        audit_logger=get_ai_audit_logger(),
        cost_calculator=get_cost_calculator(),
        usage_collector=get_token_usage_collector(),
    )


@lru_cache
def get_ai_provider_factory() -> AIProviderFactory:
    settings = get_settings()
    factory = AIProviderFactory()
    factory.register(
        AIProviderType.OPENAI,
        lambda: _wrap_chat_provider(OpenAIProvider(api_key=settings.ai.openai_api_key), settings),
    )
    factory.register(
        AIProviderType.GEMINI,
        lambda: _wrap_chat_provider(GeminiChatProvider(api_key=settings.gemini.api_key), settings),
    )
    factory.register(
        AIProviderType.CLAUDE,
        lambda: _wrap_chat_provider(
            ClaudeProvider(api_key=settings.ai.anthropic_api_key), settings
        ),
    )
    factory.register(
        AIProviderType.OLLAMA,
        lambda: _wrap_chat_provider(OllamaProvider(base_url=settings.ai.ollama_base_url), settings),
    )
    factory.register(AIProviderType.MOCK, lambda: _wrap_chat_provider(MockAIProvider(), settings))
    return factory


def _wrap_embedding_provider(
    inner: EmbeddingProviderPort, settings: Settings
) -> ResilientEmbeddingProvider:
    return ResilientEmbeddingProvider(
        inner=inner,
        retry_policy=_retry_policy(settings),
        timeout_seconds=settings.ai.request_timeout_seconds,
        audit_logger=get_ai_audit_logger(),
        cost_calculator=get_cost_calculator(),
        usage_collector=get_token_usage_collector(),
    )


@lru_cache
def get_embedding_provider_factory() -> EmbeddingProviderFactory:
    settings = get_settings()
    factory = EmbeddingProviderFactory()
    factory.register(
        AIProviderType.OPENAI,
        lambda: _wrap_embedding_provider(
            OpenAIEmbeddingProvider(api_key=settings.ai.openai_api_key), settings
        ),
    )
    factory.register(
        AIProviderType.GEMINI,
        lambda: _wrap_embedding_provider(
            GeminiEmbeddingProvider(api_key=settings.gemini.api_key), settings
        ),
    )
    factory.register(
        AIProviderType.MOCK,
        lambda: _wrap_embedding_provider(MockEmbeddingProvider(), settings),
    )
    return factory


@lru_cache
def get_ai_gateway_facade() -> AIGatewayFacade:
    """The default-provider facade future clinical modules depend on via
    `public/interfaces.py::AIGatewayPort` — resolves
    `AISettings.default_provider`/`default_embedding_provider` once at
    first use and reuses the same wired provider for the process
    lifetime (a provider adapter holds no per-call mutable state, so
    sharing it is safe)."""
    settings = get_settings()
    chat_provider = get_ai_provider_factory().create(AIProviderType(settings.ai.default_provider))
    embedding_provider = get_embedding_provider_factory().create(
        AIProviderType(settings.ai.default_embedding_provider)
    )
    return AIGatewayFacade(
        chat_completion_use_case=GenerateChatCompletion(provider=chat_provider),
        embedding_use_case=GenerateEmbedding(provider=embedding_provider),
        prompt_renderer=get_prompt_registry(),
    )
