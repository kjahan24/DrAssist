"""Unit tests for the AI SOAP Note Generation module's domain value
objects."""

from uuid import uuid4

import pytest

from app.modules.soap_note_ai.domain.enums import (
    GenerationStatus,
    PatientSex,
    SOAPNoteOutputFormat,
    SOAPStyle,
)
from app.modules.soap_note_ai.domain.exceptions import InvalidSOAPEncounterInputError
from app.modules.soap_note_ai.domain.value_objects import (
    GenerationSession,
    SOAPEncounterInput,
    SOAPNote,
    SOAPNoteStreamChunk,
    SOAPSection,
    SOAPTemplateSet,
)


def _encounter(**overrides: object) -> SOAPEncounterInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Headache",
        "soap_style": SOAPStyle.STANDARD,
    }
    defaults.update(overrides)
    return SOAPEncounterInput(**defaults)  # type: ignore[arg-type]


class TestSOAPEncounterInput:
    def test_constructs_with_required_fields_only(self) -> None:
        encounter = _encounter()
        assert encounter.chief_complaint == "Headache"
        assert encounter.language == "en"
        assert encounter.visit_id is None
        assert encounter.symptoms == ()
        assert dict(encounter.vitals) == {}
        assert encounter.patient_age is None
        assert encounter.patient_sex is None
        assert encounter.output_format is SOAPNoteOutputFormat.JSON

    def test_accepts_the_full_set_of_optional_fields(self) -> None:
        visit_id = uuid4()
        encounter = _encounter(
            visit_id=visit_id,
            history_of_present_illness="Gradual onset",
            symptoms=("throbbing", "photophobia"),
            review_of_systems="Negative except as noted",
            physical_examination="No focal deficits",
            vitals={"BP": "120/80"},
            medications=("ibuprofen 200mg",),
            allergies=("penicillin",),
            diagnoses=("tension headache",),
            assessment="Tension headache",
            plan="OTC analgesics",
            clinician_instructions="Keep it concise",
            encounter_context="Routine follow-up",
            patient_age=34,
            patient_sex=PatientSex.FEMALE,
            visit_type="Outpatient",
            language="es",
            soap_style=SOAPStyle.DETAILED,
            output_format=SOAPNoteOutputFormat.MARKDOWN,
        )
        assert encounter.visit_id == visit_id
        assert encounter.patient_age == 34
        assert encounter.patient_sex is PatientSex.FEMALE
        assert encounter.visit_type == "Outpatient"
        assert encounter.soap_style is SOAPStyle.DETAILED
        assert encounter.output_format is SOAPNoteOutputFormat.MARKDOWN

    @pytest.mark.parametrize("chief_complaint", ["", "   "])
    def test_rejects_blank_chief_complaint(self, chief_complaint: str) -> None:
        with pytest.raises(InvalidSOAPEncounterInputError):
            _encounter(chief_complaint=chief_complaint)

    @pytest.mark.parametrize("language", ["", "   "])
    def test_rejects_blank_language(self, language: str) -> None:
        with pytest.raises(InvalidSOAPEncounterInputError):
            _encounter(language=language)

    @pytest.mark.parametrize("patient_age", [-1, 151, -100])
    def test_rejects_implausible_patient_age(self, patient_age: int) -> None:
        with pytest.raises(InvalidSOAPEncounterInputError):
            _encounter(patient_age=patient_age)

    @pytest.mark.parametrize("patient_age", [0, 1, 150])
    def test_accepts_boundary_valid_ages(self, patient_age: int) -> None:
        encounter = _encounter(patient_age=patient_age)
        assert encounter.patient_age == patient_age

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


class TestSOAPSection:
    def test_constructs_with_name_and_content(self) -> None:
        section = SOAPSection(name="assessment", content="Tension headache")
        assert section.name == "assessment"
        assert section.content == "Tension headache"

    def test_equality_is_by_value(self) -> None:
        a = SOAPSection(name="plan", content="Rest")
        b = SOAPSection(name="plan", content="Rest")
        assert a == b


class TestSOAPNote:
    def _note(self, **overrides: object) -> SOAPNote:
        defaults: dict[str, object] = {
            "sections": (
                SOAPSection(name="subjective", content="Headache reported"),
                SOAPSection(name="assessment", content="Tension headache"),
            ),
            "raw_text": '{"subjective": "Headache reported"}',
            "output_format": SOAPNoteOutputFormat.JSON,
        }
        defaults.update(overrides)
        return SOAPNote(**defaults)  # type: ignore[arg-type]

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
        note = self._note(sections=(SOAPSection(name="plan", content="   "),))
        assert note.has_section("plan") is False

    def test_has_section_is_false_when_absent(self) -> None:
        note = self._note()
        assert note.has_section("objective") is False


class TestSOAPTemplateSet:
    def test_constructs_with_all_fields(self) -> None:
        template_set = SOAPTemplateSet(
            system_template_name="soap_note.standard.system",
            developer_template_name="soap_note.standard.developer",
            user_template_name="soap_note.standard.user",
            version=1,
        )
        assert template_set.version == 1
        assert template_set.system_template_name == "soap_note.standard.system"


class TestGenerationSession:
    def _session(self, **overrides: object) -> GenerationSession:
        defaults: dict[str, object] = {
            "generation_id": uuid4(),
            "provider": "mock",
            "model": "mock-model",
            "soap_style": "standard",
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


class TestSOAPNoteStreamChunk:
    def test_defaults_is_final_to_false(self) -> None:
        chunk = SOAPNoteStreamChunk(delta="hello")
        assert chunk.is_final is False

    def test_accepts_is_final_true(self) -> None:
        chunk = SOAPNoteStreamChunk(delta="", is_final=True)
        assert chunk.is_final is True
