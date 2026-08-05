"""Unit tests for `container.py`'s DI wiring."""

from uuid import uuid4

import pytest

from app.modules.patient_education_ai.container import (
    get_cost_estimator,
    get_discharge_instruction_port,
    get_discharge_instruction_service,
    get_lifestyle_recommendation_port,
    get_lifestyle_recommendation_service,
    get_output_parser,
    get_patient_education_ai_facade,
    get_patient_education_audit_logger,
    get_patient_education_generator,
    get_patient_education_port,
    get_patient_education_service,
    get_prompt_builder,
    get_renderer,
    get_result_validator,
    get_template_selector,
)
from app.modules.patient_education_ai.domain.enums import PatientEducationSetting
from app.modules.patient_education_ai.domain.exceptions import (
    InvalidPatientEducationResponseFormatError,
)
from app.modules.patient_education_ai.domain.value_objects import PatientEducationInput
from app.modules.patient_education_ai.public.facade import PatientEducationAIFacade


class TestGetPatientEducationAIFacade:
    def test_returns_a_patient_education_ai_facade(self) -> None:
        assert isinstance(get_patient_education_ai_facade(), PatientEducationAIFacade)

    def test_is_a_singleton(self) -> None:
        assert get_patient_education_ai_facade() is get_patient_education_ai_facade()

    async def test_default_wired_generation_surfaces_a_parsing_error_against_the_mock_provider(
        self,
    ) -> None:
        """AI Foundation's default `mock` provider (`AI_DEFAULT_PROVIDER`
        unset in the test environment) echoes plain, non-JSON text —
        this module's parser always expects JSON (see
        `infrastructure/parsing/patient_education_parser.py`'s own
        docstring), so the container's *default* wiring predictably
        raises `InvalidPatientEducationResponseFormatError` rather than
        silently returning a wrong-shaped result. Tests exercising a
        genuinely successful generation inject a fake/canned-JSON
        `AIGatewayPort` instead (see `infrastructure
        /test_patient_education_generator.py`)."""
        facade = get_patient_education_ai_facade()
        input_dto = PatientEducationInput(
            organization_id=uuid4(),
            patient_id=uuid4(),
            education_setting=PatientEducationSetting.ADULT,
            diagnoses=("Hypertension",),
            current_medications=("Lisinopril",),
        )

        with pytest.raises(InvalidPatientEducationResponseFormatError):
            await facade.generate_patient_education(input_dto)


class TestSingletonHelpers:
    def test_output_parser_is_a_singleton(self) -> None:
        assert get_output_parser() is get_output_parser()

    def test_patient_education_port_is_a_singleton(self) -> None:
        assert get_patient_education_port() is get_patient_education_port()

    def test_discharge_instruction_port_is_a_singleton(self) -> None:
        assert get_discharge_instruction_port() is get_discharge_instruction_port()

    def test_lifestyle_recommendation_port_is_a_singleton(self) -> None:
        assert get_lifestyle_recommendation_port() is get_lifestyle_recommendation_port()

    def test_patient_education_service_is_a_singleton(self) -> None:
        assert get_patient_education_service() is get_patient_education_service()

    def test_discharge_instruction_service_is_a_singleton(self) -> None:
        assert get_discharge_instruction_service() is get_discharge_instruction_service()

    def test_lifestyle_recommendation_service_is_a_singleton(self) -> None:
        assert get_lifestyle_recommendation_service() is get_lifestyle_recommendation_service()

    def test_renderer_is_a_singleton(self) -> None:
        assert get_renderer() is get_renderer()

    def test_result_validator_is_a_singleton(self) -> None:
        assert get_result_validator() is get_result_validator()

    def test_patient_education_audit_logger_is_a_singleton(self) -> None:
        logger_a = get_patient_education_audit_logger()
        logger_b = get_patient_education_audit_logger()
        assert logger_a is logger_b

    def test_cost_estimator_is_a_singleton(self) -> None:
        assert get_cost_estimator() is get_cost_estimator()

    def test_template_selector_is_a_singleton(self) -> None:
        assert get_template_selector() is get_template_selector()

    def test_prompt_builder_is_a_singleton(self) -> None:
        assert get_prompt_builder() is get_prompt_builder()

    def test_patient_education_generator_is_a_singleton(self) -> None:
        assert get_patient_education_generator() is get_patient_education_generator()
