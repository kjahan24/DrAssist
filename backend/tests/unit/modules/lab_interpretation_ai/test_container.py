"""Unit tests for `container.py`'s DI wiring."""

from uuid import uuid4

import pytest

from app.modules.lab_interpretation_ai.container import (
    get_cost_estimator,
    get_critical_value_analyzer,
    get_critical_value_service,
    get_lab_interpretation_ai_facade,
    get_lab_interpretation_audit_logger,
    get_lab_interpretation_generator,
    get_output_parser,
    get_prompt_builder,
    get_recommendation_service,
    get_renderer,
    get_result_validator,
    get_template_selector,
    get_trend_service,
)
from app.modules.lab_interpretation_ai.domain.enums import LabInterpretationSetting
from app.modules.lab_interpretation_ai.domain.exceptions import (
    InvalidLabInterpretationResponseFormatError,
)
from app.modules.lab_interpretation_ai.domain.value_objects import LabInterpretationInput
from app.modules.lab_interpretation_ai.public.facade import LabInterpretationAIFacade
from tests.unit.modules.lab_interpretation_ai.application.fakes import make_lab_value


class TestGetLabInterpretationAIFacade:
    def test_returns_a_lab_interpretation_ai_facade(self) -> None:
        assert isinstance(get_lab_interpretation_ai_facade(), LabInterpretationAIFacade)

    def test_is_a_singleton(self) -> None:
        assert get_lab_interpretation_ai_facade() is get_lab_interpretation_ai_facade()

    async def test_default_wired_generation_surfaces_a_parsing_error_against_the_mock_provider(
        self,
    ) -> None:
        """AI Foundation's default `mock` provider (`AI_DEFAULT_PROVIDER`
        unset in the test environment) echoes plain, non-JSON text — this
        module's parser always expects JSON (see `infrastructure/parsing
        /lab_interpretation_parser.py`'s own docstring), so the
        container's *default* wiring predictably raises
        `InvalidLabInterpretationResponseFormatError` rather than silently
        returning a wrong-shaped result. Tests exercising a genuinely
        successful generation inject a fake/canned-JSON `AIGatewayPort`
        instead (see `infrastructure
        /test_lab_interpretation_generator.py`)."""
        facade = get_lab_interpretation_ai_facade()
        input_dto = LabInterpretationInput(
            organization_id=uuid4(),
            patient_id=uuid4(),
            lab_values=(make_lab_value(),),
            lab_setting=LabInterpretationSetting.OUTPATIENT,
        )

        with pytest.raises(InvalidLabInterpretationResponseFormatError):
            await facade.generate_interpretation(input_dto)


class TestSingletonHelpers:
    def test_output_parser_is_a_singleton(self) -> None:
        assert get_output_parser() is get_output_parser()

    def test_critical_value_analyzer_is_a_singleton(self) -> None:
        assert get_critical_value_analyzer() is get_critical_value_analyzer()

    def test_critical_value_service_is_a_singleton(self) -> None:
        assert get_critical_value_service() is get_critical_value_service()

    def test_trend_service_is_a_singleton(self) -> None:
        assert get_trend_service() is get_trend_service()

    def test_recommendation_service_is_a_singleton(self) -> None:
        assert get_recommendation_service() is get_recommendation_service()

    def test_renderer_is_a_singleton(self) -> None:
        assert get_renderer() is get_renderer()

    def test_result_validator_is_a_singleton(self) -> None:
        assert get_result_validator() is get_result_validator()

    def test_lab_interpretation_audit_logger_is_a_singleton(self) -> None:
        logger_a = get_lab_interpretation_audit_logger()
        logger_b = get_lab_interpretation_audit_logger()
        assert logger_a is logger_b

    def test_cost_estimator_is_a_singleton(self) -> None:
        assert get_cost_estimator() is get_cost_estimator()

    def test_template_selector_is_a_singleton(self) -> None:
        assert get_template_selector() is get_template_selector()

    def test_prompt_builder_is_a_singleton(self) -> None:
        assert get_prompt_builder() is get_prompt_builder()

    def test_lab_interpretation_generator_is_a_singleton(self) -> None:
        assert get_lab_interpretation_generator() is get_lab_interpretation_generator()
