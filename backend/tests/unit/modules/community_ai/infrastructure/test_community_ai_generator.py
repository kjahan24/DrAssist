"""Unit tests for `DefaultCommunityAIGenerator` — this is this task's own
required "AI provider mock smoke test" quality gate: the whole
generate-summary/generate-misinformation-assessment/generate-resource-
recommendations pipeline runs end-to-end against `AIProviderType.MOCK`
and a fake in-process gateway, with zero real network calls, exercising
real template registration/rendering (`PromptRegistry`) and real JSON
parsing/validation (`_result_serialization.py`) along the way — only the
transport (`AIGatewayPort.generate_chat_completion`) is faked.
"""

from collections.abc import Iterator

import pytest

import app.modules.community_ai.infrastructure.prompts.template_registrar as registrar_module
from app.modules.ai.infrastructure.prompts.in_memory_repository import (
    InMemoryPromptTemplateRepository,
)
from app.modules.ai.infrastructure.prompts.registry import PromptRegistry
from app.modules.ai.public.dto import (
    AIFinishReason,
    AIMessage,
    AIMessageRole,
    AIModel,
    AIProviderType,
    ChatCompletionResponse,
    TokenUsage,
)
from app.modules.community_ai.domain.enums import MisinformationRiskLevel, ResourceType
from app.modules.community_ai.domain.exceptions import InvalidAnalysisResultError
from app.modules.community_ai.domain.value_objects import TrustedMedicalSource
from app.modules.community_ai.infrastructure.generation.community_ai_generator import (
    DefaultCommunityAIGenerator,
)
from tests.unit.modules.community_ai.application.fakes import FakeAIGateway


@pytest.fixture(autouse=True)
def _reset_registration_flag() -> Iterator[None]:
    registrar_module._templates_registered = False
    yield
    registrar_module._templates_registered = False


def _mock_model() -> AIModel:
    return AIModel(provider=AIProviderType.MOCK, name="mock-model")


def _generator(*, ai_gateway: FakeAIGateway | None = None) -> DefaultCommunityAIGenerator:
    gateway = ai_gateway or FakeAIGateway()
    return DefaultCommunityAIGenerator(
        ai_gateway=gateway,
        prompt_registry=PromptRegistry(repository=InMemoryPromptTemplateRepository()),
        default_model=_mock_model(),
    )


def _chat_response(content: str) -> ChatCompletionResponse:
    return ChatCompletionResponse(
        message=AIMessage(role=AIMessageRole.ASSISTANT, content=content),
        model=_mock_model(),
        provider=AIProviderType.MOCK,
        usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        finish_reason=AIFinishReason.STOP,
        latency_ms=2.5,
    )


class TestGenerateSummary:
    async def test_parses_a_valid_mock_response_end_to_end(self) -> None:
        gateway = FakeAIGateway(
            chat_response=_chat_response(
                '{"key_points": ["A"], "main_claims": [], "areas_of_agreement": [], '
                '"areas_of_disagreement": [], "unanswered_questions": [], '
                '"safety_disclaimer": null}'
            )
        )
        generator = _generator(ai_gateway=gateway)

        summary, metadata = await generator.generate_summary(title="Title", text="Body")

        assert summary.key_points == ("A",)
        assert metadata.provider == AIProviderType.MOCK.value
        assert len(gateway.received_chat_requests) == 1

    async def test_raises_invalid_result_for_malformed_json(self) -> None:
        gateway = FakeAIGateway(chat_response=_chat_response("not json"))
        generator = _generator(ai_gateway=gateway)

        with pytest.raises(InvalidAnalysisResultError):
            await generator.generate_summary(title="Title", text="Body")


class TestGenerateMisinformationAssessment:
    async def test_parses_a_valid_mock_response(self) -> None:
        gateway = FakeAIGateway(
            chat_response=_chat_response(
                '{"risk_level": "high", "claims": ["X"], "evidence_needed": true, '
                '"explanation": "Unsupported claim.", "confidence_score": 0.7, '
                '"recommended_for_moderation_review": true, "reference_suggestions": []}'
            )
        )
        generator = _generator(ai_gateway=gateway)

        assessment, _ = await generator.generate_misinformation_assessment(
            title="Title", text="Body"
        )

        assert assessment.risk_level is MisinformationRiskLevel.HIGH
        assert assessment.recommended_for_moderation_review is True


class TestGenerateResourceRecommendations:
    async def test_drops_a_recommendation_whose_url_is_not_in_the_catalog(self) -> None:
        catalog = (
            TrustedMedicalSource(
                title="MedlinePlus",
                url="https://medlineplus.gov",
                resource_type=ResourceType.WEBSITE,
            ),
        )
        gateway = FakeAIGateway(
            chat_response=_chat_response(
                '{"items": ['
                '{"source_title": "MedlinePlus", "source_url": "https://medlineplus.gov", '
                '"resource_type": "website", "relevance_explanation": "Relevant.", '
                '"confidence_score": 0.9},'
                '{"source_title": "Fabricated Source", "source_url": "https://not-real.example", '
                '"resource_type": "website", "relevance_explanation": "Invented.", '
                '"confidence_score": 0.9}'
                "]}"
            )
        )
        generator = _generator(ai_gateway=gateway)

        recommendations, _ = await generator.generate_resource_recommendations(
            title="Title", text="Body", catalog=catalog
        )

        assert len(recommendations) == 1
        assert recommendations[0].source_url == "https://medlineplus.gov"
