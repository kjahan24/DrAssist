"""Unit tests for `container.py`'s DI wiring."""

from uuid import uuid4

import pytest

from app.modules.pathology_interpretation_ai.container import (
    get_clinical_correlator,
    get_correlation_service,
    get_cost_estimator,
    get_finding_extraction_service,
    get_malignancy_assessment_service,
    get_output_parser,
    get_pathology_interpretation_ai_facade,
    get_pathology_interpretation_audit_logger,
    get_pathology_interpretation_generator,
    get_prompt_builder,
    get_result_validator,
    get_summary_service,
    get_template_selector,
)
from app.modules.pathology_interpretation_ai.domain.enums import (
    PathologyExaminationType,
    PathologySetting,
)
from app.modules.pathology_interpretation_ai.domain.exceptions import (
    InvalidPathologyInterpretationResponseFormatError,
)
from app.modules.pathology_interpretation_ai.domain.value_objects import (
    PathologyInterpretationInput,
)
from app.modules.pathology_interpretation_ai.public.facade import (
    PathologyInterpretationAIFacade,
)


class TestGetPathologyInterpretationAIFacade:
    def test_returns_a_pathology_interpretation_ai_facade(self) -> None:
        assert isinstance(get_pathology_interpretation_ai_facade(), PathologyInterpretationAIFacade)

    def test_is_a_singleton(self) -> None:
        assert get_pathology_interpretation_ai_facade() is get_pathology_interpretation_ai_facade()

    async def test_default_wired_generation_surfaces_a_parsing_error_against_the_mock_provider(
        self,
    ) -> None:
        """AI Foundation's default `mock` provider (`AI_DEFAULT_PROVIDER`
        unset in the test environment) echoes plain, non-JSON text — this
        module's parser always expects JSON (see `infrastructure/parsing
        /pathology_interpretation_parser.py`'s own docstring), so the
        container's *default* wiring predictably raises
        `InvalidPathologyInterpretationResponseFormatError` rather than
        silently returning a wrong-shaped result. Tests exercising a
        genuinely successful generation inject a fake/canned-JSON
        `AIGatewayPort` instead (see `infrastructure
        /test_pathology_interpretation_generator.py`)."""
        facade = get_pathology_interpretation_ai_facade()
        input_dto = PathologyInterpretationInput(
            organization_id=uuid4(),
            patient_id=uuid4(),
            report_text="Sections show benign glandular tissue with reactive changes noted.",
            examination_type=PathologyExaminationType.HISTOPATHOLOGY,
            pathology_setting=PathologySetting.OUTPATIENT,
        )

        with pytest.raises(InvalidPathologyInterpretationResponseFormatError):
            await facade.generate_interpretation(input_dto)


class TestSingletonHelpers:
    def test_output_parser_is_a_singleton(self) -> None:
        assert get_output_parser() is get_output_parser()

    def test_clinical_correlator_is_a_singleton(self) -> None:
        assert get_clinical_correlator() is get_clinical_correlator()

    def test_finding_extraction_service_is_a_singleton(self) -> None:
        assert get_finding_extraction_service() is get_finding_extraction_service()

    def test_malignancy_assessment_service_is_a_singleton(self) -> None:
        assert get_malignancy_assessment_service() is get_malignancy_assessment_service()

    def test_correlation_service_is_a_singleton(self) -> None:
        assert get_correlation_service() is get_correlation_service()

    def test_summary_service_is_a_singleton(self) -> None:
        assert get_summary_service() is get_summary_service()

    def test_result_validator_is_a_singleton(self) -> None:
        assert get_result_validator() is get_result_validator()

    def test_pathology_interpretation_audit_logger_is_a_singleton(self) -> None:
        logger_a = get_pathology_interpretation_audit_logger()
        logger_b = get_pathology_interpretation_audit_logger()
        assert logger_a is logger_b

    def test_cost_estimator_is_a_singleton(self) -> None:
        assert get_cost_estimator() is get_cost_estimator()

    def test_template_selector_is_a_singleton(self) -> None:
        assert get_template_selector() is get_template_selector()

    def test_prompt_builder_is_a_singleton(self) -> None:
        assert get_prompt_builder() is get_prompt_builder()

    def test_pathology_interpretation_generator_is_a_singleton(self) -> None:
        assert get_pathology_interpretation_generator() is get_pathology_interpretation_generator()
