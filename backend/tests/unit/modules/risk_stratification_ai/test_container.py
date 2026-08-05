"""Unit tests for `container.py`'s DI wiring."""

from uuid import uuid4

import pytest

from app.modules.risk_stratification_ai.container import (
    get_clinical_risk_assessment_service,
    get_clinical_risk_port,
    get_cost_estimator,
    get_early_warning_port,
    get_early_warning_service,
    get_monitoring_recommendation_service,
    get_output_parser,
    get_prompt_builder,
    get_renderer,
    get_result_validator,
    get_risk_explanation_service,
    get_risk_scoring_port,
    get_risk_scoring_service,
    get_risk_stratification_ai_facade,
    get_risk_stratification_audit_logger,
    get_risk_stratification_generator,
    get_template_selector,
)
from app.modules.risk_stratification_ai.domain.enums import RiskStratificationSetting
from app.modules.risk_stratification_ai.domain.exceptions import (
    InvalidRiskStratificationResponseFormatError,
)
from app.modules.risk_stratification_ai.domain.value_objects import (
    RiskStratificationInput,
    VitalSigns,
)
from app.modules.risk_stratification_ai.public.facade import RiskStratificationAIFacade


class TestGetRiskStratificationAIFacade:
    def test_returns_a_risk_stratification_ai_facade(self) -> None:
        assert isinstance(get_risk_stratification_ai_facade(), RiskStratificationAIFacade)

    def test_is_a_singleton(self) -> None:
        assert get_risk_stratification_ai_facade() is get_risk_stratification_ai_facade()

    async def test_default_wired_generation_surfaces_a_parsing_error_against_the_mock_provider(
        self,
    ) -> None:
        """AI Foundation's default `mock` provider (`AI_DEFAULT_PROVIDER`
        unset in the test environment) echoes plain, non-JSON text —
        this module's parser always expects JSON (see
        `infrastructure/parsing/risk_stratification_parser.py`'s own
        docstring), so the container's *default* wiring predictably
        raises `InvalidRiskStratificationResponseFormatError` rather
        than silently returning a wrong-shaped result. Tests exercising
        a genuinely successful generation inject a fake/canned-JSON
        `AIGatewayPort` instead (see `infrastructure
        /test_risk_stratification_generator.py`)."""
        facade = get_risk_stratification_ai_facade()
        input_dto = RiskStratificationInput(
            organization_id=uuid4(),
            patient_id=uuid4(),
            risk_setting=RiskStratificationSetting.OUTPATIENT,
            vital_signs=VitalSigns(respiratory_rate=16),
        )

        with pytest.raises(InvalidRiskStratificationResponseFormatError):
            await facade.analyze_patient_risk(input_dto)


class TestSingletonHelpers:
    def test_output_parser_is_a_singleton(self) -> None:
        assert get_output_parser() is get_output_parser()

    def test_risk_scoring_port_is_a_singleton(self) -> None:
        assert get_risk_scoring_port() is get_risk_scoring_port()

    def test_early_warning_port_is_a_singleton(self) -> None:
        assert get_early_warning_port() is get_early_warning_port()

    def test_clinical_risk_port_is_a_singleton(self) -> None:
        assert get_clinical_risk_port() is get_clinical_risk_port()

    def test_risk_scoring_service_is_a_singleton(self) -> None:
        assert get_risk_scoring_service() is get_risk_scoring_service()

    def test_clinical_risk_assessment_service_is_a_singleton(self) -> None:
        assert get_clinical_risk_assessment_service() is get_clinical_risk_assessment_service()

    def test_early_warning_service_is_a_singleton(self) -> None:
        assert get_early_warning_service() is get_early_warning_service()

    def test_risk_explanation_service_is_a_singleton(self) -> None:
        assert get_risk_explanation_service() is get_risk_explanation_service()

    def test_monitoring_recommendation_service_is_a_singleton(self) -> None:
        assert get_monitoring_recommendation_service() is get_monitoring_recommendation_service()

    def test_renderer_is_a_singleton(self) -> None:
        assert get_renderer() is get_renderer()

    def test_result_validator_is_a_singleton(self) -> None:
        assert get_result_validator() is get_result_validator()

    def test_risk_stratification_audit_logger_is_a_singleton(self) -> None:
        logger_a = get_risk_stratification_audit_logger()
        logger_b = get_risk_stratification_audit_logger()
        assert logger_a is logger_b

    def test_cost_estimator_is_a_singleton(self) -> None:
        assert get_cost_estimator() is get_cost_estimator()

    def test_template_selector_is_a_singleton(self) -> None:
        assert get_template_selector() is get_template_selector()

    def test_prompt_builder_is_a_singleton(self) -> None:
        assert get_prompt_builder() is get_prompt_builder()

    def test_risk_stratification_generator_is_a_singleton(self) -> None:
        assert get_risk_stratification_generator() is get_risk_stratification_generator()
