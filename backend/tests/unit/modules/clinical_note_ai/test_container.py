"""Unit tests for `container.py`'s DI wiring."""

from uuid import uuid4

import pytest

from app.modules.clinical_note_ai.container import (
    get_clinical_note_ai_facade,
    get_clinical_note_audit_logger,
    get_clinical_note_generator,
    get_cost_estimator,
    get_note_renderer,
    get_note_validator,
    get_output_parser,
    get_prompt_builder,
    get_template_selector,
)
from app.modules.clinical_note_ai.domain.enums import NoteStyle
from app.modules.clinical_note_ai.domain.exceptions import InvalidClinicalNoteFormatError
from app.modules.clinical_note_ai.domain.value_objects import ClinicalEncounterInput
from app.modules.clinical_note_ai.public.facade import ClinicalNoteAIFacade


class TestGetClinicalNoteAIFacade:
    def test_returns_a_clinical_note_ai_facade(self) -> None:
        assert isinstance(get_clinical_note_ai_facade(), ClinicalNoteAIFacade)

    def test_is_a_singleton(self) -> None:
        assert get_clinical_note_ai_facade() is get_clinical_note_ai_facade()

    async def test_default_wired_generation_surfaces_a_parsing_error_against_the_mock_provider(
        self,
    ) -> None:
        """AI Foundation's default `mock` provider (`AI_DEFAULT_PROVIDER`
        unset in the test environment) echoes plain, non-JSON text — this
        module's parser always expects JSON (see `infrastructure/parsing
        /clinical_note_parser.py`'s own docstring), so the container's
        *default* wiring predictably raises `InvalidClinicalNoteFormatError`
        rather than silently returning a wrong-shaped note. Tests exercising
        a genuinely successful generation inject a fake/canned-JSON
        `AIGatewayPort` instead (see `infrastructure
        /test_clinical_note_generator.py`)."""
        facade = get_clinical_note_ai_facade()
        encounter = ClinicalEncounterInput(
            organization_id=uuid4(),
            patient_id=uuid4(),
            chief_complaint="Headache",
            note_style=NoteStyle.CONCISE,
        )

        with pytest.raises(InvalidClinicalNoteFormatError):
            await facade.generate_note(encounter)


class TestSingletonHelpers:
    def test_output_parser_is_a_singleton(self) -> None:
        assert get_output_parser() is get_output_parser()

    def test_note_validator_is_a_singleton(self) -> None:
        assert get_note_validator() is get_note_validator()

    def test_clinical_note_audit_logger_is_a_singleton(self) -> None:
        assert get_clinical_note_audit_logger() is get_clinical_note_audit_logger()

    def test_cost_estimator_is_a_singleton(self) -> None:
        assert get_cost_estimator() is get_cost_estimator()

    def test_template_selector_is_a_singleton(self) -> None:
        assert get_template_selector() is get_template_selector()

    def test_prompt_builder_is_a_singleton(self) -> None:
        assert get_prompt_builder() is get_prompt_builder()

    def test_note_renderer_is_a_singleton(self) -> None:
        assert get_note_renderer() is get_note_renderer()

    def test_clinical_note_generator_is_a_singleton(self) -> None:
        assert get_clinical_note_generator() is get_clinical_note_generator()
