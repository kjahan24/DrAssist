"""Provider-specific exception mapping.

Classifies an exception raised by *any* provider SDK client (OpenAI,
Anthropic, google-generativeai, or an `httpx` error from the Ollama
adapter's raw HTTP calls) into this module's own normalized
`AIProviderError` hierarchy (`domain/exceptions.py`).

Matches on the raised exception's **class name**, not `isinstance` against
the real SDK's exception classes — deliberately: every SDK (`openai`,
`anthropic`) is an optional dependency this module lazily imports only
when a real adapter is actually invoked (`openai_provider.py`,
`claude_provider.py`), so a central mapper that had to `import openai`
just to `isinstance`-check its exceptions would force that dependency to
be installed even when only, say, `MockAIProvider`/`OllamaProvider` are in
use. Every major provider SDK already names its exceptions
predictably (`RateLimitError`, `AuthenticationError`, `APITimeoutError`,
`BadRequestError`, ...), so this is both dependency-free and, in
practice, exact.

`httpx` is the one exception: it's already a hard base dependency (used
directly by `infrastructure/llm/ollama_provider.py`), and it reports every
HTTP error through a single `HTTPStatusError` class regardless of status
code — class-name matching alone can't distinguish a 401 from a 429 from
a 500 for that adapter, so `httpx.HTTPStatusError` is `isinstance`-checked
explicitly and classified by `response.status_code` instead.
"""

import httpx

from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.exceptions import (
    AIProviderAuthenticationError,
    AIProviderError,
    AIProviderInvalidRequestError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)

_AUTH_MARKERS = ("Authentication", "PermissionDenied", "Unauthorized", "Forbidden")
_RATE_LIMIT_MARKERS = ("RateLimit", "TooManyRequests")
_TIMEOUT_MARKERS = ("Timeout",)
_INVALID_REQUEST_MARKERS = (
    "BadRequest",
    "InvalidRequest",
    "UnprocessableEntity",
    "NotFound",
    "ValidationError",
)
_UNAVAILABLE_MARKERS = (
    "Connection",
    "InternalServerError",
    "ServiceUnavailable",
    "APIStatusError",
    "APIError",
)


def classify_provider_exception(exc: Exception, *, provider: AIProviderType) -> AIProviderError:
    if isinstance(exc, AIProviderError):
        return exc

    if isinstance(exc, httpx.HTTPStatusError):
        return _classify_http_status_error(exc, provider=provider)
    if isinstance(exc, httpx.TimeoutException):
        return AIProviderTimeoutError(
            provider=provider.value, message=str(exc) or "request timed out"
        )
    if isinstance(exc, httpx.HTTPError):
        return AIProviderUnavailableError(
            provider=provider.value, message=str(exc) or type(exc).__name__
        )

    class_name = type(exc).__name__
    message = str(exc) or class_name

    if any(marker in class_name for marker in _RATE_LIMIT_MARKERS):
        return AIProviderRateLimitError(provider=provider.value, message=message)
    if any(marker in class_name for marker in _TIMEOUT_MARKERS):
        return AIProviderTimeoutError(provider=provider.value, message=message)
    if any(marker in class_name for marker in _AUTH_MARKERS):
        return AIProviderAuthenticationError(provider=provider.value, message=message)
    if any(marker in class_name for marker in _INVALID_REQUEST_MARKERS):
        return AIProviderInvalidRequestError(provider=provider.value, message=message)
    if any(marker in class_name for marker in _UNAVAILABLE_MARKERS):
        return AIProviderUnavailableError(provider=provider.value, message=message)

    # Unknown failure shape: treated as unavailable (retryable) rather than
    # silently swallowed — matches this module's "fail loud, let the caller
    # see a normalized AIProviderError" contract, and errs toward retrying
    # an unrecognized transient-looking failure rather than not.
    return AIProviderUnavailableError(provider=provider.value, message=message)


def _classify_http_status_error(
    exc: httpx.HTTPStatusError, *, provider: AIProviderType
) -> AIProviderError:
    status_code = exc.response.status_code
    message = f"HTTP {status_code}: {exc.response.text[:500]}"
    if status_code in (401, 403):
        return AIProviderAuthenticationError(provider=provider.value, message=message)
    if status_code == 429:
        retry_after = exc.response.headers.get("Retry-After")
        return AIProviderRateLimitError(
            provider=provider.value,
            message=message,
            retry_after_seconds=float(retry_after) if retry_after else None,
        )
    if status_code == 408:
        return AIProviderTimeoutError(provider=provider.value, message=message)
    if 400 <= status_code < 500:
        return AIProviderInvalidRequestError(provider=provider.value, message=message)
    return AIProviderUnavailableError(provider=provider.value, message=message)
