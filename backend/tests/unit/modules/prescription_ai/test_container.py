"""Unit tests for `container.py`'s DI wiring."""

from uuid import uuid4

import pytest

from app.modules.prescription_ai.container import (
    get_cost_estimator,
    get_drug_interaction_checker,
    get_medication_knowledge_base,
    get_output_parser,
    get_prescription_ai_facade,
    get_prescription_audit_logger,
    get_prescription_generator,
    get_prompt_builder,
    get_safety_analysis_service,
    get_suggestion_renderer,
    get_suggestion_validator,
    get_template_selector,
)
from app.modules.prescription_ai.domain.enums import PrescribingSetting
from app.modules.prescription_ai.domain.exceptions import InvalidPrescriptionResponseFormatError
from app.modules.prescription_ai.domain.value_objects import PrescriptionContextInput
from app.modules.prescription_ai.public.facade import PrescriptionAIFacade


class TestGetPrescriptionAIFacade:
    def test_returns_a_prescription_ai_facade(self) -> None:
        assert isinstance(get_prescription_ai_facade(), PrescriptionAIFacade)

    def test_is_a_singleton(self) -> None:
        assert get_prescription_ai_facade() is get_prescription_ai_facade()

    async def test_default_wired_generation_surfaces_a_parsing_error_against_the_mock_provider(
        self,
    ) -> None:
        """AI Foundation's default `mock` provider (`AI_DEFAULT_PROVIDER`
        unset in the test environment) echoes plain, non-JSON text — this
        module's parser always expects JSON (see `infrastructure/parsing
        /prescription_suggestion_parser.py`'s own docstring), so the
        container's *default* wiring predictably raises
        `InvalidPrescriptionResponseFormatError` rather than silently
        returning a wrong-shaped suggestion set. Tests exercising a
        genuinely successful generation inject a fake/canned-JSON
        `AIGatewayPort` instead (see `infrastructure
        /test_prescription_generator.py`)."""
        facade = get_prescription_ai_facade()
        context = PrescriptionContextInput(
            organization_id=uuid4(),
            patient_id=uuid4(),
            chief_complaint="Sore throat",
            prescribing_setting=PrescribingSetting.OUTPATIENT,
        )

        with pytest.raises(InvalidPrescriptionResponseFormatError):
            await facade.generate_suggestion(context)


class TestSingletonHelpers:
    def test_output_parser_is_a_singleton(self) -> None:
        assert get_output_parser() is get_output_parser()

    def test_medication_knowledge_base_is_a_singleton(self) -> None:
        assert get_medication_knowledge_base() is get_medication_knowledge_base()

    def test_drug_interaction_checker_is_a_singleton(self) -> None:
        assert get_drug_interaction_checker() is get_drug_interaction_checker()

    def test_suggestion_validator_is_a_singleton(self) -> None:
        assert get_suggestion_validator() is get_suggestion_validator()

    def test_prescription_audit_logger_is_a_singleton(self) -> None:
        assert get_prescription_audit_logger() is get_prescription_audit_logger()

    def test_cost_estimator_is_a_singleton(self) -> None:
        assert get_cost_estimator() is get_cost_estimator()

    def test_template_selector_is_a_singleton(self) -> None:
        assert get_template_selector() is get_template_selector()

    def test_prompt_builder_is_a_singleton(self) -> None:
        assert get_prompt_builder() is get_prompt_builder()

    def test_safety_analysis_service_is_a_singleton(self) -> None:
        assert get_safety_analysis_service() is get_safety_analysis_service()

    def test_suggestion_renderer_is_a_singleton(self) -> None:
        assert get_suggestion_renderer() is get_suggestion_renderer()

    def test_prescription_generator_is_a_singleton(self) -> None:
        assert get_prescription_generator() is get_prescription_generator()
