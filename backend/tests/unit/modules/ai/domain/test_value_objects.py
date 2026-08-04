"""Unit tests for the AI module's domain value objects."""

import pytest

from app.modules.ai.domain.enums import AIMessageRole, AIProviderType
from app.modules.ai.domain.exceptions import InvalidPromptTemplateError
from app.modules.ai.domain.value_objects import (
    AIMessage,
    AIModel,
    CostEstimate,
    PromptTemplate,
    TokenUsage,
)


class TestTokenUsage:
    def test_constructs_with_valid_counts(self) -> None:
        usage = TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        assert usage.prompt_tokens == 10
        assert usage.total_tokens == 15

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"prompt_tokens": -1, "completion_tokens": 0, "total_tokens": 0},
            {"prompt_tokens": 0, "completion_tokens": -1, "total_tokens": 0},
            {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": -1},
        ],
    )
    def test_rejects_negative_counts(self, kwargs: dict[str, int]) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            TokenUsage(**kwargs)

    def test_addition_sums_each_field(self) -> None:
        a = TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        b = TokenUsage(prompt_tokens=3, completion_tokens=2, total_tokens=5)
        combined = a + b
        assert combined == TokenUsage(prompt_tokens=13, completion_tokens=7, total_tokens=20)

    def test_zero_is_the_additive_identity(self) -> None:
        usage = TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        assert usage + TokenUsage.zero() == usage

    def test_equality_is_by_value(self) -> None:
        assert TokenUsage(prompt_tokens=1, completion_tokens=2, total_tokens=3) == TokenUsage(
            prompt_tokens=1, completion_tokens=2, total_tokens=3
        )


class TestAIModel:
    def test_constructs_with_minimal_fields(self) -> None:
        model = AIModel(provider=AIProviderType.OPENAI, name="gpt-4o-mini")
        assert model.name == "gpt-4o-mini"
        assert model.supports_streaming is False

    def test_rejects_blank_name(self) -> None:
        with pytest.raises(ValueError, match="must not be blank"):
            AIModel(provider=AIProviderType.OPENAI, name="   ")

    @pytest.mark.parametrize("context_window", [0, -1])
    def test_rejects_non_positive_context_window(self, context_window: int) -> None:
        with pytest.raises(ValueError, match="context_window"):
            AIModel(
                provider=AIProviderType.OPENAI, name="gpt-4o-mini", context_window=context_window
            )

    @pytest.mark.parametrize("max_output_tokens", [0, -1])
    def test_rejects_non_positive_max_output_tokens(self, max_output_tokens: int) -> None:
        with pytest.raises(ValueError, match="max_output_tokens"):
            AIModel(
                provider=AIProviderType.OPENAI,
                name="gpt-4o-mini",
                max_output_tokens=max_output_tokens,
            )

    def test_same_name_different_provider_is_a_different_model(self) -> None:
        openai_model = AIModel(provider=AIProviderType.OPENAI, name="shared-name")
        ollama_model = AIModel(provider=AIProviderType.OLLAMA, name="shared-name")
        assert openai_model != ollama_model


class TestAIMessage:
    def test_constructs_with_role_and_content(self) -> None:
        message = AIMessage(role=AIMessageRole.USER, content="hello")
        assert message.role is AIMessageRole.USER
        assert message.content == "hello"
        assert message.name is None

    def test_equality_is_by_value(self) -> None:
        a = AIMessage(role=AIMessageRole.USER, content="hi")
        b = AIMessage(role=AIMessageRole.USER, content="hi")
        assert a == b


class TestCostEstimate:
    def test_total_cost_sums_input_and_output(self) -> None:
        estimate = CostEstimate(input_cost_usd=0.01, output_cost_usd=0.02)
        assert estimate.total_cost_usd == pytest.approx(0.03)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"input_cost_usd": -0.01, "output_cost_usd": 0},
            {"input_cost_usd": 0, "output_cost_usd": -0.01},
        ],
    )
    def test_rejects_negative_components(self, kwargs: dict[str, float]) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            CostEstimate(**kwargs)


class TestPromptTemplate:
    def test_constructs_with_valid_fields(self) -> None:
        template = PromptTemplate(name="greeting", version=1, template_string="Hello {{ name }}!")
        assert template.name == "greeting"
        assert template.version == 1

    def test_rejects_blank_name(self) -> None:
        with pytest.raises(InvalidPromptTemplateError):
            PromptTemplate(name="  ", version=1, template_string="hello")

    def test_rejects_version_below_one(self) -> None:
        with pytest.raises(InvalidPromptTemplateError):
            PromptTemplate(name="greeting", version=0, template_string="hello")

    def test_rejects_blank_template_string(self) -> None:
        with pytest.raises(InvalidPromptTemplateError):
            PromptTemplate(name="greeting", version=1, template_string="   ")

    def test_equality_is_by_value(self) -> None:
        a = PromptTemplate(name="greeting", version=1, template_string="hi")
        b = PromptTemplate(name="greeting", version=1, template_string="hi")
        assert a == b
