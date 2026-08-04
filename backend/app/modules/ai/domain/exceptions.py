"""Domain exceptions for the AI module.

`AIProviderError` and its subclasses are the **normalized** exception
vocabulary every `infrastructure/llm/`/`infrastructure/embeddings/`
adapter maps its own SDK's exceptions onto (see
`infrastructure/providers/exception_mapping.py`) — an Application-layer
use case, or a future clinical module calling this module's `public/`
facade, only ever needs to handle this one small hierarchy, never
`openai.RateLimitError` vs. `anthropic.RateLimitError` vs. a raw
`httpx.TimeoutException` individually.

`retryable` is a class attribute, not something each call site decides —
`infrastructure/providers/retry.py` reads it directly, so "is this
transient" is answered once, in the same place the exception is defined,
per this codebase's own "retry transient errors only, fail fast on bad
input" rule (`09_ai_gateway_and_storage.md`).
"""

from app.shared.domain.exceptions import DomainError


class AIProviderError(DomainError):
    """Base class for every normalized provider-call failure."""

    retryable: bool = False

    def __init__(self, *, provider: str, message: str) -> None:
        super().__init__(f"[{provider}] {message}")
        self.provider = provider
        self.message = message


class AIProviderAuthenticationError(AIProviderError):
    """Bad/missing API key. Never retried — a fourth attempt with the same
    invalid credential fails identically to the first."""

    retryable = False


class AIProviderInvalidRequestError(AIProviderError):
    """Malformed request (bad model name, message shape the provider
    rejects, ...). Never retried — the same request fails identically."""

    retryable = False


class AIProviderRateLimitError(AIProviderError):
    """Transient — the same request typically succeeds after backing off."""

    retryable = True

    def __init__(
        self, *, provider: str, message: str, retry_after_seconds: float | None = None
    ) -> None:
        super().__init__(provider=provider, message=message)
        self.retry_after_seconds = retry_after_seconds


class AIProviderTimeoutError(AIProviderError):
    """Raised by `infrastructure/providers/timeout.py` when a call exceeds
    its configured budget, and by adapters that map a provider SDK's own
    timeout exception. Transient — worth one more attempt."""

    retryable = True


class AIProviderUnavailableError(AIProviderError):
    """5xx / connection-level failure on the provider's side. Transient."""

    retryable = True


class AIProviderResponseParsingError(AIProviderError):
    """The provider replied, but its payload couldn't be turned into the
    structured shape the caller expected (see
    `infrastructure/parsers/json_parser.py`). Not retried by default — a
    malformed response is usually deterministic for the same input,
    though a caller may choose to retry with a stricter prompt."""

    retryable = False


class UnsupportedAIProviderError(DomainError):
    """`AIProviderFactory`/`EmbeddingProviderFactory` was asked to build a
    provider type with no adapter registered for it."""

    def __init__(self, provider: str) -> None:
        super().__init__(f"no adapter registered for AI provider {provider!r}")
        self.provider = provider


class PromptTemplateNotFoundError(DomainError):
    def __init__(self, name: str, version: int | None = None) -> None:
        if version is None:
            super().__init__(f"no prompt template named {name!r}")
        else:
            super().__init__(f"no prompt template named {name!r} at version {version}")
        self.name = name
        self.version = version


class DuplicatePromptTemplateVersionError(DomainError):
    def __init__(self, name: str, version: int) -> None:
        super().__init__(f"prompt template {name!r} version {version} is already registered")
        self.name = name
        self.version = version


class PromptVariableMissingError(DomainError):
    def __init__(self, template_name: str, variable_name: str) -> None:
        super().__init__(
            f"prompt template {template_name!r} requires variable {variable_name!r}, "
            "which was not supplied"
        )
        self.template_name = template_name
        self.variable_name = variable_name


class InvalidPromptTemplateError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid prompt template: {reason}")
        self.reason = reason
