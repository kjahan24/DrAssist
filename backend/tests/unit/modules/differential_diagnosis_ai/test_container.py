"""Unit tests for `container.py`'s DI wiring."""

from uuid import uuid4

import pytest

from app.modules.differential_diagnosis_ai.container import (
    get_clinical_reasoning_advisor,
    get_cost_estimator,
    get_differential_diagnosis_ai_facade,
    get_differential_diagnosis_audit_logger,
    get_differential_diagnosis_generator,
    get_output_parser,
    get_prompt_builder,
    get_ranking_service,
    get_reasoning_service,
    get_result_renderer,
    get_result_validator,
    get_template_selector,
)
from app.modules.differential_diagnosis_ai.domain.enums import ClinicalSetting
from app.modules.differential_diagnosis_ai.domain.exceptions import (
    InvalidDifferentialResponseFormatError,
)
from app.modules.differential_diagnosis_ai.domain.value_objects import DifferentialDiagnosisInput
from app.modules.differential_diagnosis_ai.public.facade import DifferentialDiagnosisAIFacade


class TestGetDifferentialDiagnosisAIFacade:
    def test_returns_a_differential_diagnosis_ai_facade(self) -> None:
        assert isinstance(get_differential_diagnosis_ai_facade(), DifferentialDiagnosisAIFacade)

    def test_is_a_singleton(self) -> None:
        assert get_differential_diagnosis_ai_facade() is get_differential_diagnosis_ai_facade()

    async def test_default_wired_generation_surfaces_a_parsing_error_against_the_mock_provider(
        self,
    ) -> None:
        """AI Foundation's default `mock` provider (`AI_DEFAULT_PROVIDER`
        unset in the test environment) echoes plain, non-JSON text — this
        module's parser always expects JSON (see `infrastructure/parsing
        /differential_diagnosis_parser.py`'s own docstring), so the
        container's *default* wiring predictably raises
        `InvalidDifferentialResponseFormatError` rather than silently
        returning a wrong-shaped result. Tests exercising a genuinely
        successful generation inject a fake/canned-JSON `AIGatewayPort`
        instead (see `infrastructure
        /test_differential_diagnosis_generator.py`)."""
        facade = get_differential_diagnosis_ai_facade()
        evidence = DifferentialDiagnosisInput(
            organization_id=uuid4(),
            patient_id=uuid4(),
            chief_complaint="Chest pain",
            clinical_setting=ClinicalSetting.OUTPATIENT,
        )

        with pytest.raises(InvalidDifferentialResponseFormatError):
            await facade.generate_differential_diagnosis(evidence)


class TestSingletonHelpers:
    def test_output_parser_is_a_singleton(self) -> None:
        assert get_output_parser() is get_output_parser()

    def test_clinical_reasoning_advisor_is_a_singleton(self) -> None:
        assert get_clinical_reasoning_advisor() is get_clinical_reasoning_advisor()

    def test_result_validator_is_a_singleton(self) -> None:
        assert get_result_validator() is get_result_validator()

    def test_differential_diagnosis_audit_logger_is_a_singleton(self) -> None:
        logger_a = get_differential_diagnosis_audit_logger()
        logger_b = get_differential_diagnosis_audit_logger()
        assert logger_a is logger_b

    def test_cost_estimator_is_a_singleton(self) -> None:
        assert get_cost_estimator() is get_cost_estimator()

    def test_template_selector_is_a_singleton(self) -> None:
        assert get_template_selector() is get_template_selector()

    def test_prompt_builder_is_a_singleton(self) -> None:
        assert get_prompt_builder() is get_prompt_builder()

    def test_reasoning_service_is_a_singleton(self) -> None:
        assert get_reasoning_service() is get_reasoning_service()

    def test_ranking_service_is_a_singleton(self) -> None:
        assert get_ranking_service() is get_ranking_service()

    def test_result_renderer_is_a_singleton(self) -> None:
        assert get_result_renderer() is get_result_renderer()

    def test_differential_diagnosis_generator_is_a_singleton(self) -> None:
        assert get_differential_diagnosis_generator() is get_differential_diagnosis_generator()
