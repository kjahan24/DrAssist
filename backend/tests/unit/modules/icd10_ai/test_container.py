"""Unit tests for `container.py`'s DI wiring."""

from uuid import uuid4

import pytest

from app.modules.icd10_ai.container import (
    get_cost_estimator,
    get_icd10_ai_facade,
    get_icd10_audit_logger,
    get_icd10_generator,
    get_knowledge_base,
    get_output_parser,
    get_prompt_builder,
    get_ranking_service,
    get_suggestion_renderer,
    get_suggestion_validator,
    get_template_selector,
)
from app.modules.icd10_ai.domain.enums import CodingSetting
from app.modules.icd10_ai.domain.exceptions import InvalidICD10ResponseFormatError
from app.modules.icd10_ai.domain.value_objects import ICD10CodingInput
from app.modules.icd10_ai.public.facade import ICD10AIFacade


class TestGetICD10AIFacade:
    def test_returns_an_icd10_ai_facade(self) -> None:
        assert isinstance(get_icd10_ai_facade(), ICD10AIFacade)

    def test_is_a_singleton(self) -> None:
        assert get_icd10_ai_facade() is get_icd10_ai_facade()

    async def test_default_wired_generation_surfaces_a_parsing_error_against_the_mock_provider(
        self,
    ) -> None:
        """AI Foundation's default `mock` provider (`AI_DEFAULT_PROVIDER`
        unset in the test environment) echoes plain, non-JSON text — this
        module's parser always expects JSON (see `infrastructure/parsing
        /icd10_suggestion_parser.py`'s own docstring), so the container's
        *default* wiring predictably raises
        `InvalidICD10ResponseFormatError` rather than silently returning
        a wrong-shaped suggestion set. Tests exercising a genuinely
        successful generation inject a fake/canned-JSON `AIGatewayPort`
        instead (see `infrastructure/test_icd10_generator.py`)."""
        facade = get_icd10_ai_facade()
        coding_input = ICD10CodingInput(
            organization_id=uuid4(),
            patient_id=uuid4(),
            chief_complaint="Sore throat",
            coding_setting=CodingSetting.OUTPATIENT,
        )

        with pytest.raises(InvalidICD10ResponseFormatError):
            await facade.generate_suggestions(coding_input)


class TestSingletonHelpers:
    def test_output_parser_is_a_singleton(self) -> None:
        assert get_output_parser() is get_output_parser()

    def test_knowledge_base_is_a_singleton(self) -> None:
        assert get_knowledge_base() is get_knowledge_base()

    def test_suggestion_validator_is_a_singleton(self) -> None:
        assert get_suggestion_validator() is get_suggestion_validator()

    def test_icd10_audit_logger_is_a_singleton(self) -> None:
        assert get_icd10_audit_logger() is get_icd10_audit_logger()

    def test_cost_estimator_is_a_singleton(self) -> None:
        assert get_cost_estimator() is get_cost_estimator()

    def test_template_selector_is_a_singleton(self) -> None:
        assert get_template_selector() is get_template_selector()

    def test_prompt_builder_is_a_singleton(self) -> None:
        assert get_prompt_builder() is get_prompt_builder()

    def test_ranking_service_is_a_singleton(self) -> None:
        assert get_ranking_service() is get_ranking_service()

    def test_suggestion_renderer_is_a_singleton(self) -> None:
        assert get_suggestion_renderer() is get_suggestion_renderer()

    def test_icd10_generator_is_a_singleton(self) -> None:
        assert get_icd10_generator() is get_icd10_generator()
