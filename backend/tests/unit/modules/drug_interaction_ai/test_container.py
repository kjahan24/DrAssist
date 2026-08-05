"""Unit tests for `container.py`'s DI wiring."""

from uuid import uuid4

import pytest

from app.modules.drug_interaction_ai.container import (
    get_alternative_medication_service,
    get_contraindication_service,
    get_cost_estimator,
    get_dose_adjustment_port,
    get_dose_adjustment_service,
    get_drug_interaction_ai_facade,
    get_drug_interaction_audit_logger,
    get_drug_interaction_generator,
    get_drug_interaction_port,
    get_drug_interaction_service,
    get_interaction_evidence_port,
    get_medication_safety_port,
    get_medication_safety_service,
    get_output_parser,
    get_prompt_builder,
    get_renderer,
    get_result_validator,
    get_template_selector,
)
from app.modules.drug_interaction_ai.domain.enums import DrugInteractionSetting
from app.modules.drug_interaction_ai.domain.exceptions import (
    InvalidDrugInteractionResponseFormatError,
)
from app.modules.drug_interaction_ai.domain.value_objects import (
    DrugInteractionAnalysisInput,
    MedicationEntry,
)
from app.modules.drug_interaction_ai.public.facade import DrugInteractionAIFacade


class TestGetDrugInteractionAIFacade:
    def test_returns_a_drug_interaction_ai_facade(self) -> None:
        assert isinstance(get_drug_interaction_ai_facade(), DrugInteractionAIFacade)

    def test_is_a_singleton(self) -> None:
        assert get_drug_interaction_ai_facade() is get_drug_interaction_ai_facade()

    async def test_default_wired_generation_surfaces_a_parsing_error_against_the_mock_provider(
        self,
    ) -> None:
        """AI Foundation's default `mock` provider (`AI_DEFAULT_PROVIDER`
        unset in the test environment) echoes plain, non-JSON text — this
        module's parser always expects JSON (see `infrastructure/parsing
        /drug_safety_analysis_parser.py`'s own docstring), so the
        container's *default* wiring predictably raises
        `InvalidDrugInteractionResponseFormatError` rather than silently
        returning a wrong-shaped result. Tests exercising a genuinely
        successful generation inject a fake/canned-JSON `AIGatewayPort`
        instead (see `infrastructure
        /test_drug_safety_analysis_generator.py`)."""
        facade = get_drug_interaction_ai_facade()
        input_dto = DrugInteractionAnalysisInput(
            organization_id=uuid4(),
            patient_id=uuid4(),
            medication_setting=DrugInteractionSetting.OUTPATIENT,
            current_medications=(MedicationEntry(drug_name="Warfarin"),),
        )

        with pytest.raises(InvalidDrugInteractionResponseFormatError):
            await facade.analyze_medication_safety(input_dto)


class TestSingletonHelpers:
    def test_output_parser_is_a_singleton(self) -> None:
        assert get_output_parser() is get_output_parser()

    def test_drug_interaction_port_is_a_singleton(self) -> None:
        assert get_drug_interaction_port() is get_drug_interaction_port()

    def test_interaction_evidence_port_is_a_singleton(self) -> None:
        assert get_interaction_evidence_port() is get_interaction_evidence_port()

    def test_medication_safety_port_is_a_singleton(self) -> None:
        assert get_medication_safety_port() is get_medication_safety_port()

    def test_dose_adjustment_port_is_a_singleton(self) -> None:
        assert get_dose_adjustment_port() is get_dose_adjustment_port()

    def test_drug_interaction_service_is_a_singleton(self) -> None:
        assert get_drug_interaction_service() is get_drug_interaction_service()

    def test_medication_safety_service_is_a_singleton(self) -> None:
        assert get_medication_safety_service() is get_medication_safety_service()

    def test_contraindication_service_is_a_singleton(self) -> None:
        assert get_contraindication_service() is get_contraindication_service()

    def test_dose_adjustment_service_is_a_singleton(self) -> None:
        assert get_dose_adjustment_service() is get_dose_adjustment_service()

    def test_alternative_medication_service_is_a_singleton(self) -> None:
        assert get_alternative_medication_service() is get_alternative_medication_service()

    def test_renderer_is_a_singleton(self) -> None:
        assert get_renderer() is get_renderer()

    def test_result_validator_is_a_singleton(self) -> None:
        assert get_result_validator() is get_result_validator()

    def test_drug_interaction_audit_logger_is_a_singleton(self) -> None:
        logger_a = get_drug_interaction_audit_logger()
        logger_b = get_drug_interaction_audit_logger()
        assert logger_a is logger_b

    def test_cost_estimator_is_a_singleton(self) -> None:
        assert get_cost_estimator() is get_cost_estimator()

    def test_template_selector_is_a_singleton(self) -> None:
        assert get_template_selector() is get_template_selector()

    def test_prompt_builder_is_a_singleton(self) -> None:
        assert get_prompt_builder() is get_prompt_builder()

    def test_drug_interaction_generator_is_a_singleton(self) -> None:
        assert get_drug_interaction_generator() is get_drug_interaction_generator()
