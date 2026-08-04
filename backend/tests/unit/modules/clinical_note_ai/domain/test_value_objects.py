"""Unit tests for the AI Clinical Note Generation module's domain value
objects."""

from uuid import uuid4

import pytest

from app.modules.clinical_note_ai.domain.enums import (
    ClinicalNoteOutputFormat,
    GenerationStatus,
    NoteStyle,
)
from app.modules.clinical_note_ai.domain.exceptions import InvalidClinicalEncounterInputError
from app.modules.clinical_note_ai.domain.value_objects import (
    ClinicalEncounterInput,
    ClinicalNote,
    ClinicalNoteSection,
    ClinicalNoteStreamChunk,
    ClinicalNoteTemplateSet,
    GenerationSession,
)


def _encounter(**overrides: object) -> ClinicalEncounterInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Headache",
        "note_style": NoteStyle.CONCISE,
    }
    defaults.update(overrides)
    return ClinicalEncounterInput(**defaults)  # type: ignore[arg-type]


class TestClinicalEncounterInput:
    def test_constructs_with_required_fields_only(self) -> None:
        encounter = _encounter()
        assert encounter.chief_complaint == "Headache"
        assert encounter.language == "en"
        assert encounter.visit_id is None
        assert encounter.symptoms == ()
        assert encounter.allergies == ()
        assert dict(encounter.vitals) == {}
        assert encounter.output_format is ClinicalNoteOutputFormat.JSON

    def test_accepts_the_full_set_of_optional_fields(self) -> None:
        visit_id = uuid4()
        encounter = _encounter(
            visit_id=visit_id,
            history_of_present_illness="Gradual onset",
            symptoms=("throbbing", "photophobia"),
            observations=("alert", "oriented"),
            physical_examination="No focal deficits",
            assessment="Tension headache",
            plan="OTC analgesics",
            medications=("ibuprofen 200mg",),
            allergies=("penicillin",),
            vitals={"BP": "120/80", "HR": "72"},
            diagnoses=("tension headache",),
            clinician_instructions="Keep it concise",
            encounter_context="Routine follow-up",
            language="es",
            note_style=NoteStyle.DETAILED,
            output_format=ClinicalNoteOutputFormat.MARKDOWN,
        )
        assert encounter.visit_id == visit_id
        assert encounter.symptoms == ("throbbing", "photophobia")
        assert encounter.vitals == {"BP": "120/80", "HR": "72"}
        assert encounter.note_style is NoteStyle.DETAILED
        assert encounter.output_format is ClinicalNoteOutputFormat.MARKDOWN

    @pytest.mark.parametrize("chief_complaint", ["", "   "])
    def test_rejects_blank_chief_complaint(self, chief_complaint: str) -> None:
        with pytest.raises(InvalidClinicalEncounterInputError):
            _encounter(chief_complaint=chief_complaint)

    @pytest.mark.parametrize("language", ["", "   "])
    def test_rejects_blank_language(self, language: str) -> None:
        with pytest.raises(InvalidClinicalEncounterInputError):
            _encounter(language=language)

    def test_equality_is_by_value(self) -> None:
        organization_id = uuid4()
        patient_id = uuid4()
        a = _encounter(organization_id=organization_id, patient_id=patient_id)
        b = _encounter(organization_id=organization_id, patient_id=patient_id)
        assert a == b

    def test_default_vitals_are_not_shared_across_instances(self) -> None:
        a = _encounter()
        b = _encounter()
        assert a.vitals is not b.vitals


class TestClinicalNoteSection:
    def test_constructs_with_name_and_content(self) -> None:
        section = ClinicalNoteSection(name="assessment", content="Tension headache")
        assert section.name == "assessment"
        assert section.content == "Tension headache"

    def test_equality_is_by_value(self) -> None:
        a = ClinicalNoteSection(name="plan", content="Rest")
        b = ClinicalNoteSection(name="plan", content="Rest")
        assert a == b


class TestClinicalNote:
    def _note(self, **overrides: object) -> ClinicalNote:
        defaults: dict[str, object] = {
            "sections": (
                ClinicalNoteSection(name="chief_complaint", content="Headache"),
                ClinicalNoteSection(name="assessment", content="Tension headache"),
            ),
            "raw_text": '{"chief_complaint": "Headache"}',
            "output_format": ClinicalNoteOutputFormat.JSON,
        }
        defaults.update(overrides)
        return ClinicalNote(**defaults)  # type: ignore[arg-type]

    def test_get_section_returns_matching_content(self) -> None:
        note = self._note()
        assert note.get_section("assessment") == "Tension headache"

    def test_get_section_is_case_and_whitespace_insensitive(self) -> None:
        note = self._note()
        assert note.get_section("  Assessment  ") == "Tension headache"

    def test_get_section_returns_none_when_absent(self) -> None:
        note = self._note()
        assert note.get_section("plan") is None

    def test_has_section_is_true_for_non_blank_content(self) -> None:
        note = self._note()
        assert note.has_section("assessment") is True

    def test_has_section_is_false_for_blank_content(self) -> None:
        note = self._note(sections=(ClinicalNoteSection(name="plan", content="   "),))
        assert note.has_section("plan") is False

    def test_has_section_is_false_when_absent(self) -> None:
        note = self._note()
        assert note.has_section("review_of_systems") is False


class TestClinicalNoteTemplateSet:
    def test_constructs_with_all_fields(self) -> None:
        template_set = ClinicalNoteTemplateSet(
            system_template_name="clinical_note.concise.system",
            developer_template_name="clinical_note.concise.developer",
            user_template_name="clinical_note.concise.user",
            version=1,
        )
        assert template_set.version == 1
        assert template_set.system_template_name == "clinical_note.concise.system"


class TestGenerationSession:
    def _session(self, **overrides: object) -> GenerationSession:
        defaults: dict[str, object] = {
            "generation_id": uuid4(),
            "provider": "mock",
            "model": "mock-model",
            "note_style": "concise",
            "language": "en",
            "status": GenerationStatus.COMPLETED,
        }
        defaults.update(overrides)
        return GenerationSession(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_defaults_for_metrics(self) -> None:
        session = self._session()
        assert session.latency_ms == 0.0
        assert session.prompt_tokens == 0
        assert session.estimated_cost_usd == 0.0
        assert session.created_at is not None

    def test_accepts_full_metrics(self) -> None:
        session = self._session(
            latency_ms=42.5,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=0.0021,
        )
        assert session.latency_ms == 42.5
        assert session.total_tokens == 150

    def test_equality_is_by_value(self) -> None:
        generation_id = uuid4()
        a = self._session(generation_id=generation_id)
        b = self._session(generation_id=generation_id, created_at=a.created_at)
        assert a == b

    def test_different_generation_ids_are_never_equal(self) -> None:
        a = self._session(generation_id=uuid4())
        b = self._session(generation_id=uuid4())
        assert a != b


class TestClinicalNoteStreamChunk:
    def test_defaults_is_final_to_false(self) -> None:
        chunk = ClinicalNoteStreamChunk(delta="hello")
        assert chunk.is_final is False

    def test_accepts_is_final_true(self) -> None:
        chunk = ClinicalNoteStreamChunk(delta="", is_final=True)
        assert chunk.is_final is True
