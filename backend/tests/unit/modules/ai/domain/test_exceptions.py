"""Unit tests for the AI module's domain exceptions — mainly the
`retryable` classification `infrastructure/providers/retry.py` depends on,
since a regression there silently changes retry behavior."""

from app.modules.ai.domain.exceptions import (
    AIProviderAuthenticationError,
    AIProviderInvalidRequestError,
    AIProviderRateLimitError,
    AIProviderResponseParsingError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    DuplicatePromptTemplateVersionError,
    PromptTemplateNotFoundError,
    PromptVariableMissingError,
    UnsupportedAIProviderError,
)


class TestRetryableClassification:
    def test_rate_limit_is_retryable(self) -> None:
        assert AIProviderRateLimitError(provider="openai", message="429").retryable is True

    def test_timeout_is_retryable(self) -> None:
        assert AIProviderTimeoutError(provider="openai", message="timed out").retryable is True

    def test_unavailable_is_retryable(self) -> None:
        assert AIProviderUnavailableError(provider="openai", message="503").retryable is True

    def test_authentication_is_not_retryable(self) -> None:
        assert AIProviderAuthenticationError(provider="openai", message="401").retryable is False

    def test_invalid_request_is_not_retryable(self) -> None:
        assert AIProviderInvalidRequestError(provider="openai", message="400").retryable is False

    def test_response_parsing_is_not_retryable(self) -> None:
        assert (
            AIProviderResponseParsingError(provider="openai", message="bad json").retryable is False
        )


class TestExceptionMessages:
    def test_rate_limit_carries_retry_after(self) -> None:
        exc = AIProviderRateLimitError(provider="openai", message="429", retry_after_seconds=1.5)
        assert exc.retry_after_seconds == 1.5

    def test_prompt_template_not_found_without_version(self) -> None:
        exc = PromptTemplateNotFoundError("greeting")
        assert "greeting" in str(exc)
        assert exc.version is None

    def test_prompt_template_not_found_with_version(self) -> None:
        exc = PromptTemplateNotFoundError("greeting", 2)
        assert "version 2" in str(exc)

    def test_duplicate_prompt_template_version_message(self) -> None:
        exc = DuplicatePromptTemplateVersionError("greeting", 1)
        assert exc.name == "greeting"
        assert exc.version == 1

    def test_prompt_variable_missing_message(self) -> None:
        exc = PromptVariableMissingError("greeting", "name")
        assert exc.template_name == "greeting"
        assert exc.variable_name == "name"

    def test_unsupported_provider_message(self) -> None:
        exc = UnsupportedAIProviderError("carrier-pigeon")
        assert "carrier-pigeon" in str(exc)
