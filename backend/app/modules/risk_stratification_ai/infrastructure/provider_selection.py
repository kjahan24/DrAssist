"""`resolve_default_ai_model` — mirrors
`app.modules.drug_interaction_ai.infrastructure.provider_selection
.resolve_default_ai_model` exactly (duplicated locally for the same
module-boundary reason `infrastructure/cost/cost_estimator.py`
documents): AI Foundation's `AIGatewayPort` is built once around a single
configured provider (`AISettings.default_provider`), so this resolves
the matching model name for whichever provider that is, rather than
hardcoding one.
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
