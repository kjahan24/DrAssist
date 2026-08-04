"""Unit tests for `DefaultICD10Generator`, including its `stream_generate`
(chunked-single-call) streaming support."""

from collections.abc import Iterator
from uuid import uuid4

import pytest

import app.modules.icd10_ai.infrastructure.prompts.template_registrar as registrar_module
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
from app.modules.icd10_ai.domain.enums import CodingSetting, GenerationStatus
from app.modules.icd10_ai.domain.value_objects import ICD10CodingInput
from app.modules.icd10_ai.infrastructure.generation.icd10_generator import DefaultICD10Generator
from app.modules.icd10_ai.infrastructure.prompts.prompt_builder import DefaultICD10PromptBuilder
from app.modules.icd10_ai.infrastructure.prompts.template_selector import (
    DefaultICD10TemplateSelector,
)
from tests.unit.modules.icd10_ai.application.fakes import FakeAIGateway, FakeCostEstimator


@pytest.fixture(autouse=True)
def _reset_registration_flag() -> Iterator[None]:
    registrar_module._templates_registered = False
    yield
    registrar_module._templates_registered = False


def _coding_input(**overrides: object) -> ICD10CodingInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Sore throat",
        "coding_setting": CodingSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return ICD10CodingInput(**defaults)  # type: ignore[arg-type]


def _generator(*, ai_gateway: FakeAIGateway | None = None) -> DefaultICD10Generator:
    gateway = ai_gateway or FakeAIGateway()
    return DefaultICD10Generator(
        ai_gateway=gateway,
        prompt_registry=PromptRegistry(repository=InMemoryPromptTemplateRepository()),
        template_selector=DefaultICD10TemplateSelector(),
        prompt_builder=DefaultICD10PromptBuilder(ai_gateway=gateway),
        cost_estimator=FakeCostEstimator(fixed_cost=0.0055),
        default_model=AIModel(provider=AIProviderType.MOCK, name="mock-model"),
    )


class TestGenerate:
    async def test_returns_raw_text_and_a_completed_session(self) -> None:
        generator = _generator()

        raw_text, session = await generator.generate(_coding_input())

        assert raw_text == '{"result": "ok"}'
        assert session.status is GenerationStatus.COMPLETED

    async def test_session_carries_provider_and_model_from_the_response(self) -> None:
        gateway = FakeAIGateway(
            chat_response=ChatCompletionResponse(
                message=AIMessage(role=AIMessageRole.ASSISTANT, content="{}"),
                model=AIModel(provider=AIProviderType.OPENAI, name="gpt-4o-mini"),
                provider=AIProviderType.OPENAI,
                usage=TokenUsage(prompt_tokens=20, completion_tokens=10, total_tokens=30),
                finish_reason=AIFinishReason.STOP,
                latency_ms=5.0,
            )
        )
        generator = _generator(ai_gateway=gateway)

        _raw_text, session = await generator.generate(_coding_input())

        assert session.provider == "openai"
        assert session.model == "gpt-4o-mini"
        assert session.prompt_tokens == 20
        assert session.completion_tokens == 10
        assert session.total_tokens == 30

    async def test_session_carries_coding_setting_and_language_from_the_input(self) -> None:
        generator = _generator()

        _raw_text, session = await generator.generate(
            _coding_input(coding_setting=CodingSetting.EMERGENCY, language="fr")
        )

        assert session.coding_setting == "emergency"
        assert session.language == "fr"

    async def test_session_carries_the_cost_estimate(self) -> None:
        generator = _generator()

        _raw_text, session = await generator.generate(_coding_input())

        assert session.estimated_cost_usd == 0.0055

    async def test_registers_templates_before_rendering(self) -> None:
        assert registrar_module._templates_registered is False
        generator = _generator()

        await generator.generate(_coding_input())

        assert registrar_module._templates_registered is True

    async def test_sends_the_configured_default_model(self) -> None:
        gateway = FakeAIGateway()
        generator = _generator(ai_gateway=gateway)

        await generator.generate(_coding_input())

        assert gateway.received_chat_requests[-1].model.name == "mock-model"

    async def test_propagates_ai_foundation_errors_unwrapped(self) -> None:
        class _FakeFoundationError(Exception):
            pass

        gateway = FakeAIGateway(chat_error=_FakeFoundationError("provider unavailable"))
        generator = _generator(ai_gateway=gateway)

        with pytest.raises(_FakeFoundationError):
            await generator.generate(_coding_input())


class TestStreamGenerate:
    async def test_yields_word_chunks_reconstructing_the_full_text(self) -> None:
        gateway = FakeAIGateway(
            chat_response=ChatCompletionResponse(
                message=AIMessage(role=AIMessageRole.ASSISTANT, content="one two three"),
                model=AIModel(provider=AIProviderType.MOCK, name="mock-model"),
                provider=AIProviderType.MOCK,
                usage=TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
                finish_reason=AIFinishReason.STOP,
                latency_ms=1.0,
            )
        )
        generator = _generator(ai_gateway=gateway)

        chunks = [chunk async for chunk in generator.stream_generate(_coding_input())]

        assert "".join(c.delta for c in chunks) == "one two three"

    async def test_only_the_last_chunk_is_final(self) -> None:
        generator = _generator()

        chunks = [chunk async for chunk in generator.stream_generate(_coding_input())]

        assert all(not c.is_final for c in chunks[:-1])
        assert chunks[-1].is_final is True

    async def test_propagates_ai_foundation_errors_unwrapped(self) -> None:
        class _FakeFoundationError(Exception):
            pass

        gateway = FakeAIGateway(chat_error=_FakeFoundationError("timed out"))
        generator = _generator(ai_gateway=gateway)

        with pytest.raises(_FakeFoundationError):
            async for _chunk in generator.stream_generate(_coding_input()):
                pass
