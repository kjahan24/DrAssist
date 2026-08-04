"""Unit tests for `classify_provider_exception`."""

import httpx
import pytest

from app.modules.ai.domain.enums import AIProviderType
from app.modules.ai.domain.exceptions import (
    AIProviderAuthenticationError,
    AIProviderError,
    AIProviderInvalidRequestError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)
from app.modules.ai.infrastructure.providers.exception_mapping import classify_provider_exception


class TestClassifyByClassName:
    @pytest.mark.parametrize(
        "class_name,expected",
        [
            ("RateLimitError", AIProviderRateLimitError),
            ("APITimeoutError", AIProviderTimeoutError),
            ("AuthenticationError", AIProviderAuthenticationError),
            ("PermissionDeniedError", AIProviderAuthenticationError),
            ("BadRequestError", AIProviderInvalidRequestError),
            ("InvalidRequestError", AIProviderInvalidRequestError),
            ("APIConnectionError", AIProviderUnavailableError),
            ("InternalServerError", AIProviderUnavailableError),
        ],
    )
    def test_maps_known_class_names(self, class_name: str, expected: type[AIProviderError]) -> None:
        exc_type = type(class_name, (Exception,), {})
        result = classify_provider_exception(exc_type("boom"), provider=AIProviderType.OPENAI)
        assert isinstance(result, expected)

    def test_unknown_exception_shape_falls_back_to_unavailable(self) -> None:
        result = classify_provider_exception(
            RuntimeError("mystery"), provider=AIProviderType.OPENAI
        )
        assert isinstance(result, AIProviderUnavailableError)

    def test_already_normalized_error_passes_through_unchanged(self) -> None:
        original = AIProviderTimeoutError(provider="openai", message="already normalized")
        result = classify_provider_exception(original, provider=AIProviderType.OPENAI)
        assert result is original

    def test_provider_is_recorded_on_the_normalized_error(self) -> None:
        result = classify_provider_exception(RuntimeError("x"), provider=AIProviderType.CLAUDE)
        assert result.provider == "claude"


class TestClassifyHttpxErrors:
    def test_401_maps_to_authentication_error(self) -> None:
        response = httpx.Response(
            401, text="unauthorized", request=httpx.Request("GET", "http://x")
        )
        exc = httpx.HTTPStatusError("401", request=response.request, response=response)
        result = classify_provider_exception(exc, provider=AIProviderType.OLLAMA)
        assert isinstance(result, AIProviderAuthenticationError)

    def test_429_maps_to_rate_limit_error_with_retry_after(self) -> None:
        request = httpx.Request("GET", "http://x")
        response = httpx.Response(429, headers={"Retry-After": "2"}, request=request)
        exc = httpx.HTTPStatusError("429", request=request, response=response)
        result = classify_provider_exception(exc, provider=AIProviderType.OLLAMA)
        assert isinstance(result, AIProviderRateLimitError)
        assert result.retry_after_seconds == 2.0

    def test_400_maps_to_invalid_request_error(self) -> None:
        request = httpx.Request("GET", "http://x")
        response = httpx.Response(400, request=request)
        exc = httpx.HTTPStatusError("400", request=request, response=response)
        result = classify_provider_exception(exc, provider=AIProviderType.OLLAMA)
        assert isinstance(result, AIProviderInvalidRequestError)

    def test_500_maps_to_unavailable_error(self) -> None:
        request = httpx.Request("GET", "http://x")
        response = httpx.Response(500, request=request)
        exc = httpx.HTTPStatusError("500", request=request, response=response)
        result = classify_provider_exception(exc, provider=AIProviderType.OLLAMA)
        assert isinstance(result, AIProviderUnavailableError)

    def test_timeout_exception_maps_to_timeout_error(self) -> None:
        exc = httpx.ConnectTimeout("timed out")
        result = classify_provider_exception(exc, provider=AIProviderType.OLLAMA)
        assert isinstance(result, AIProviderTimeoutError)

    def test_connect_error_maps_to_unavailable_error(self) -> None:
        exc = httpx.ConnectError("connection refused")
        result = classify_provider_exception(exc, provider=AIProviderType.OLLAMA)
        assert isinstance(result, AIProviderUnavailableError)
