"""Unit tests for `container.py`'s DI wiring."""

from uuid import uuid4

import pytest

from app.modules.medical_reasoning_ai.container import (
    get_confidence_calculator,
    get_confidence_service,
    get_cost_estimator,
    get_evidence_analyzer,
    get_evidence_service,
    get_medical_reasoning_ai_facade,
    get_medical_reasoning_audit_logger,
    get_medical_reasoning_generator,
    get_output_parser,
    get_prompt_builder,
    get_recommendation_service,
    get_result_validator,
    get_summary_service,
    get_template_selector,
)
from app.modules.medical_reasoning_ai.domain.enums import ReasoningSetting
from app.modules.medical_reasoning_ai.domain.exceptions import (
    InvalidMedicalReasoningResponseFormatError,
)
from app.modules.medical_reasoning_ai.domain.value_objects import MedicalReasoningInput
from app.modules.medical_reasoning_ai.public.facade import MedicalReasoningAIFacade


class TestGetMedicalReasoningAIFacade:
    def test_returns_a_medical_reasoning_ai_facade(self) -> None:
        assert isinstance(get_medical_reasoning_ai_facade(), MedicalReasoningAIFacade)

    def test_is_a_singleton(self) -> None:
        assert get_medical_reasoning_ai_facade() is get_medical_reasoning_ai_facade()

    async def test_default_wired_generation_surfaces_a_parsing_error_against_the_mock_provider(
        self,
    ) -> None:
        """AI Foundation's default `mock` provider (`AI_DEFAULT_PROVIDER`
        unset in the test environment) echoes plain, non-JSON text — this
        module's parser always expects JSON (see `infrastructure/parsing
        /medical_reasoning_parser.py`'s own docstring), so the
        container's *default* wiring predictably raises
        `InvalidMedicalReasoningResponseFormatError` rather than silently
        returning a wrong-shaped result. Tests exercising a genuinely
        successful generation inject a fake/canned-JSON `AIGatewayPort`
        instead (see `infrastructure
        /test_medical_reasoning_generator.py`)."""
        facade = get_medical_reasoning_ai_facade()
        evidence = MedicalReasoningInput(
            organization_id=uuid4(),
            patient_id=uuid4(),
            chief_complaint="Chest pain",
            reasoning_setting=ReasoningSetting.OUTPATIENT,
        )

        with pytest.raises(InvalidMedicalReasoningResponseFormatError):
            await facade.generate_reasoning(evidence)


class TestSingletonHelpers:
    def test_output_parser_is_a_singleton(self) -> None:
        assert get_output_parser() is get_output_parser()

    def test_evidence_analyzer_is_a_singleton(self) -> None:
        assert get_evidence_analyzer() is get_evidence_analyzer()

    def test_confidence_calculator_is_a_singleton(self) -> None:
        assert get_confidence_calculator() is get_confidence_calculator()

    def test_evidence_service_is_a_singleton(self) -> None:
        assert get_evidence_service() is get_evidence_service()

    def test_confidence_service_is_a_singleton(self) -> None:
        assert get_confidence_service() is get_confidence_service()

    def test_recommendation_service_is_a_singleton(self) -> None:
        assert get_recommendation_service() is get_recommendation_service()

    def test_summary_service_is_a_singleton(self) -> None:
        assert get_summary_service() is get_summary_service()

    def test_result_validator_is_a_singleton(self) -> None:
        assert get_result_validator() is get_result_validator()

    def test_medical_reasoning_audit_logger_is_a_singleton(self) -> None:
        logger_a = get_medical_reasoning_audit_logger()
        logger_b = get_medical_reasoning_audit_logger()
        assert logger_a is logger_b

    def test_cost_estimator_is_a_singleton(self) -> None:
        assert get_cost_estimator() is get_cost_estimator()

    def test_template_selector_is_a_singleton(self) -> None:
        assert get_template_selector() is get_template_selector()

    def test_prompt_builder_is_a_singleton(self) -> None:
        assert get_prompt_builder() is get_prompt_builder()

    def test_medical_reasoning_generator_is_a_singleton(self) -> None:
        assert get_medical_reasoning_generator() is get_medical_reasoning_generator()
