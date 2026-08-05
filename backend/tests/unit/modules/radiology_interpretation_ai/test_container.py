"""Unit tests for `container.py`'s DI wiring."""

from uuid import uuid4

import pytest

from app.modules.radiology_interpretation_ai.container import (
    get_cost_estimator,
    get_critical_finding_service,
    get_finding_extraction_service,
    get_finding_extractor,
    get_output_parser,
    get_prompt_builder,
    get_radiology_interpretation_ai_facade,
    get_radiology_interpretation_audit_logger,
    get_radiology_interpretation_generator,
    get_recommendation_service,
    get_result_validator,
    get_summary_service,
    get_template_selector,
)
from app.modules.radiology_interpretation_ai.domain.enums import (
    RadiologyExaminationType,
    RadiologySetting,
)
from app.modules.radiology_interpretation_ai.domain.exceptions import (
    InvalidRadiologyInterpretationResponseFormatError,
)
from app.modules.radiology_interpretation_ai.domain.value_objects import (
    RadiologyInterpretationInput,
)
from app.modules.radiology_interpretation_ai.public.facade import RadiologyInterpretationAIFacade


class TestGetRadiologyInterpretationAIFacade:
    def test_returns_a_radiology_interpretation_ai_facade(self) -> None:
        assert isinstance(get_radiology_interpretation_ai_facade(), RadiologyInterpretationAIFacade)

    def test_is_a_singleton(self) -> None:
        assert get_radiology_interpretation_ai_facade() is get_radiology_interpretation_ai_facade()

    async def test_default_wired_generation_surfaces_a_parsing_error_against_the_mock_provider(
        self,
    ) -> None:
        """AI Foundation's default `mock` provider (`AI_DEFAULT_PROVIDER`
        unset in the test environment) echoes plain, non-JSON text — this
        module's parser always expects JSON (see `infrastructure/parsing
        /radiology_interpretation_parser.py`'s own docstring), so the
        container's *default* wiring predictably raises
        `InvalidRadiologyInterpretationResponseFormatError` rather than
        silently returning a wrong-shaped result. Tests exercising a
        genuinely successful generation inject a fake/canned-JSON
        `AIGatewayPort` instead (see `infrastructure
        /test_radiology_interpretation_generator.py`)."""
        facade = get_radiology_interpretation_ai_facade()
        input_dto = RadiologyInterpretationInput(
            organization_id=uuid4(),
            patient_id=uuid4(),
            report_text="The lungs are clear bilaterally. No acute abnormality.",
            examination_type=RadiologyExaminationType.CHEST_XRAY,
            radiology_setting=RadiologySetting.OUTPATIENT,
        )

        with pytest.raises(InvalidRadiologyInterpretationResponseFormatError):
            await facade.generate_interpretation(input_dto)


class TestSingletonHelpers:
    def test_output_parser_is_a_singleton(self) -> None:
        assert get_output_parser() is get_output_parser()

    def test_finding_extractor_is_a_singleton(self) -> None:
        assert get_finding_extractor() is get_finding_extractor()

    def test_finding_extraction_service_is_a_singleton(self) -> None:
        assert get_finding_extraction_service() is get_finding_extraction_service()

    def test_critical_finding_service_is_a_singleton(self) -> None:
        assert get_critical_finding_service() is get_critical_finding_service()

    def test_recommendation_service_is_a_singleton(self) -> None:
        assert get_recommendation_service() is get_recommendation_service()

    def test_summary_service_is_a_singleton(self) -> None:
        assert get_summary_service() is get_summary_service()

    def test_result_validator_is_a_singleton(self) -> None:
        assert get_result_validator() is get_result_validator()

    def test_radiology_interpretation_audit_logger_is_a_singleton(self) -> None:
        logger_a = get_radiology_interpretation_audit_logger()
        logger_b = get_radiology_interpretation_audit_logger()
        assert logger_a is logger_b

    def test_cost_estimator_is_a_singleton(self) -> None:
        assert get_cost_estimator() is get_cost_estimator()

    def test_template_selector_is_a_singleton(self) -> None:
        assert get_template_selector() is get_template_selector()

    def test_prompt_builder_is_a_singleton(self) -> None:
        assert get_prompt_builder() is get_prompt_builder()

    def test_radiology_interpretation_generator_is_a_singleton(self) -> None:
        assert get_radiology_interpretation_generator() is get_radiology_interpretation_generator()
