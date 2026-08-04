"""`resolve_default_ai_model` — the "Provider Selection" stage's only real
degree of freedom this module has, given AI Foundation's current public
contract (see `application/services/clinical_copilot_service.py`'s own
docstring for the full reasoning): AI Foundation's `AIGatewayPort` is
built once around a single configured provider
(`AISettings.default_provider`), so this module cannot choose a
*different* provider — it can only make sure the `AIModel` it attaches to
each request names the right model for whichever provider AI Foundation
is actually configured to use, so `OpenAIProvider`/`ClaudeProvider`/...
receive a model string that exists for them, rather than e.g. an
OpenAI-shaped model name being sent to Claude.

Reads `app.core.config.Settings` directly — allowed at this module's
`container.py`/`infrastructure/` layer (every module receives
configuration this way, `06_configuration_logging_exceptions.md`), not
inside `application/`.
"""

from app.core.config import Settings
from app.modules.ai.public.dto import AIModel, AIProviderType

_MOCK_MODEL_NAME = "mock-model"


def resolve_default_ai_model(settings: Settings) -> AIModel:
    provider = AIProviderType(settings.ai.default_provider)
    if provider is AIProviderType.OPENAI:
        name = settings.ai.openai_model
    elif provider is AIProviderType.GEMINI:
        name = settings.gemini.model
    elif provider is AIProviderType.CLAUDE:
        name = settings.ai.anthropic_model
    elif provider is AIProviderType.OLLAMA:
        name = settings.ai.ollama_model
    else:
        name = _MOCK_MODEL_NAME
    return AIModel(provider=provider, name=name)
