"""Unit tests for the AI ICD-10 Coding module's domain value objects."""

from uuid import uuid4

import pytest

from app.modules.icd10_ai.domain.enums import (
    CodingSetting,
    DiagnosisFlag,
    GenerationStatus,
    ICD10OutputFormat,
    PatientSex,
)
from app.modules.icd10_ai.domain.exceptions import InvalidClinicalContextError
from app.modules.icd10_ai.domain.value_objects import (
    GenerationSession,
    ICD10CodingInput,
    ICD10StreamChunk,
    ICD10Suggestion,
    ICD10SuggestionSet,
    ICD10TemplateSet,
)


def _coding_input(**overrides: object) -> ICD10CodingInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Sore throat",
        "coding_setting": CodingSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return ICD10CodingInput(**defaults)  # type: ignore[arg-type]


class TestICD10CodingInput:
    def test_constructs_with_required_fields_only(self) -> None:
        coding_input = _coding_input()
        assert coding_input.chief_complaint == "Sore throat"
        assert coding_input.language == "en"
        assert coding_input.visit_id is None
        assert coding_input.symptoms == ()
        assert coding_input.existing_diagnoses == ()
        assert coding_input.patient_age is None
        assert coding_input.patient_sex is None
        assert coding_input.output_format is ICD10OutputFormat.JSON

    def test_accepts_the_full_set_of_optional_fields(self) -> None:
        visit_id = uuid4()
        coding_input = _coding_input(
            visit_id=visit_id,
            history_of_present_illness="Gradual onset over 2 days",
            symptoms=("sore throat", "fever"),
            review_of_systems="Negative except as noted",
            physical_examination="Erythematous pharynx",
            assessment="Acute pharyngitis",
            plan="Supportive care",
            clinical_note="Full clinical note text",
            soap_note="Full SOAP note text",
            existing_diagnoses=("seasonal allergies",),
            visit_context="Routine outpatient visit",
            patient_age=29,
            patient_sex=PatientSex.FEMALE,
            language="es",
            coding_setting=CodingSetting.EMERGENCY,
            output_format=ICD10OutputFormat.MARKDOWN,
        )
        assert coding_input.visit_id == visit_id
        assert coding_input.patient_age == 29
        assert coding_input.patient_sex is PatientSex.FEMALE
        assert coding_input.coding_setting is CodingSetting.EMERGENCY
        assert coding_input.output_format is ICD10OutputFormat.MARKDOWN

    @pytest.mark.parametrize("chief_complaint", ["", "   "])
    def test_rejects_blank_chief_complaint(self, chief_complaint: str) -> None:
        with pytest.raises(InvalidClinicalContextError):
            _coding_input(chief_complaint=chief_complaint)

    @pytest.mark.parametrize("language", ["", "   "])
    def test_rejects_blank_language(self, language: str) -> None:
        with pytest.raises(InvalidClinicalContextError):
            _coding_input(language=language)

    @pytest.mark.parametrize("patient_age", [-1, 151, -100])
    def test_rejects_implausible_patient_age(self, patient_age: int) -> None:
        with pytest.raises(InvalidClinicalContextError):
            _coding_input(patient_age=patient_age)

    @pytest.mark.parametrize("patient_age", [0, 1, 150])
    def test_accepts_boundary_valid_ages(self, patient_age: int) -> None:
        coding_input = _coding_input(patient_age=patient_age)
        assert coding_input.patient_age == patient_age

    def test_equality_is_by_value(self) -> None:
        organization_id = uuid4()
        patient_id = uuid4()
        a = _coding_input(organization_id=organization_id, patient_id=patient_id)
        b = _coding_input(organization_id=organization_id, patient_id=patient_id)
        assert a == b


class TestICD10Suggestion:
    def _suggestion(self, **overrides: object) -> ICD10Suggestion:
        defaults: dict[str, object] = {
            "icd10_code": "J06.9",
            "diagnosis_name": "Acute upper respiratory infection, unspecified",
            "confidence_score": 0.9,
            "clinical_reasoning": "Supported by sore throat and fever",
            "supporting_evidence": "sore throat, fever",
            "flag": DiagnosisFlag.PRIMARY,
        }
        defaults.update(overrides)
        return ICD10Suggestion(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_all_fields(self) -> None:
        suggestion = self._suggestion()
        assert suggestion.icd10_code == "J06.9"
        assert suggestion.confidence_score == 0.9
        assert suggestion.flag is DiagnosisFlag.PRIMARY

    def test_accepts_a_null_confidence_score(self) -> None:
        suggestion = self._suggestion(confidence_score=None)
        assert suggestion.confidence_score is None

    def test_equality_is_by_value(self) -> None:
        a = self._suggestion()
        b = self._suggestion()
        assert a == b


class TestICD10SuggestionSet:
    def _suggestion_set(self, **overrides: object) -> ICD10SuggestionSet:
        defaults: dict[str, object] = {
            "suggestions": (
                ICD10Suggestion(
                    icd10_code="J06.9",
                    diagnosis_name="Acute URI, unspecified",
                    confidence_score=0.9,
                    clinical_reasoning="Reasoning A",
                    supporting_evidence="Evidence A",
                    flag=DiagnosisFlag.PRIMARY,
                ),
                ICD10Suggestion(
                    icd10_code="R50.9",
                    diagnosis_name="Fever, unspecified",
                    confidence_score=0.6,
                    clinical_reasoning="Reasoning B",
                    supporting_evidence="Evidence B",
                    flag=DiagnosisFlag.SECONDARY,
                ),
            ),
            "raw_text": '{"suggestions": []}',
            "output_format": ICD10OutputFormat.JSON,
        }
        defaults.update(overrides)
        return ICD10SuggestionSet(**defaults)  # type: ignore[arg-type]

    def test_is_empty_is_false_when_populated(self) -> None:
        assert self._suggestion_set().is_empty is False

    def test_is_empty_is_true_when_no_suggestions(self) -> None:
        assert self._suggestion_set(suggestions=()).is_empty is True

    def test_primary_suggestions_returns_only_primary_flagged(self) -> None:
        suggestion_set = self._suggestion_set()
        primaries = suggestion_set.primary_suggestions
        assert len(primaries) == 1
        assert primaries[0].icd10_code == "J06.9"

    def test_secondary_suggestions_returns_only_secondary_flagged(self) -> None:
        suggestion_set = self._suggestion_set()
        secondaries = suggestion_set.secondary_suggestions
        assert len(secondaries) == 1
        assert secondaries[0].icd10_code == "R50.9"


class TestICD10TemplateSet:
    def test_constructs_with_all_fields(self) -> None:
        template_set = ICD10TemplateSet(
            system_template_name="icd10_suggestion.outpatient.system",
            developer_template_name="icd10_suggestion.outpatient.developer",
            user_template_name="icd10_suggestion.outpatient.user",
            version=1,
        )
        assert template_set.version == 1
        assert template_set.system_template_name == "icd10_suggestion.outpatient.system"


class TestGenerationSession:
    def _session(self, **overrides: object) -> GenerationSession:
        defaults: dict[str, object] = {
            "generation_id": uuid4(),
            "provider": "mock",
            "model": "mock-model",
            "coding_setting": "outpatient",
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

    def test_different_generation_ids_are_never_equal(self) -> None:
        a = self._session(generation_id=uuid4())
        b = self._session(generation_id=uuid4())
        assert a != b


class TestICD10StreamChunk:
    def test_defaults_is_final_to_false(self) -> None:
        chunk = ICD10StreamChunk(delta="hello")
        assert chunk.is_final is False

    def test_accepts_is_final_true(self) -> None:
        chunk = ICD10StreamChunk(delta="", is_final=True)
        assert chunk.is_final is True
