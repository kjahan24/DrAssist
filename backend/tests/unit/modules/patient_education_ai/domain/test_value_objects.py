"""Tests for the AI Patient Education & Discharge Instructions module's
domain value objects — construction, `__post_init__` validation, and
computed properties."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.patient_education_ai.domain.enums import (
    EducationGenerationStatus,
    PatientEducationOutputFormat,
    PatientEducationSetting,
)
from app.modules.patient_education_ai.domain.exceptions import (
    InvalidPatientEducationInputError,
    MissingDiagnosisError,
    MissingMedicationListError,
)
from app.modules.patient_education_ai.domain.value_objects import (
    GenerationSession,
    PatientEducationInput,
    PatientEducationResult,
    PatientEducationStreamChunk,
    PatientEducationTemplateSet,
)


class TestPatientEducationInput:
    def _valid_kwargs(self) -> dict[str, object]:
        return {
            "organization_id": uuid4(),
            "patient_id": uuid4(),
            "education_setting": PatientEducationSetting.ADULT,
            "diagnoses": ("Hypertension",),
            "current_medications": ("Lisinopril",),
        }

    def test_valid_minimal_construction(self) -> None:
        input_dto = PatientEducationInput(**self._valid_kwargs())  # type: ignore[arg-type]
        assert input_dto.language == "en"
        assert input_dto.output_format is PatientEducationOutputFormat.JSON
        assert input_dto.patient_age is None
        assert input_dto.prescription_ai_output is None

    def test_empty_diagnoses_raises_missing_diagnosis_error(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["diagnoses"] = ()
        with pytest.raises(MissingDiagnosisError):
            PatientEducationInput(**kwargs)  # type: ignore[arg-type]

    def test_empty_current_medications_raises_missing_medication_list_error(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["current_medications"] = ()
        with pytest.raises(MissingMedicationListError):
            PatientEducationInput(**kwargs)  # type: ignore[arg-type]

    def test_blank_language_raises(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["language"] = "   "
        with pytest.raises(InvalidPatientEducationInputError):
            PatientEducationInput(**kwargs)  # type: ignore[arg-type]

    @pytest.mark.parametrize("patient_age", [-1, 151])
    def test_out_of_range_patient_age_raises(self, patient_age: int) -> None:
        kwargs = self._valid_kwargs()
        kwargs["patient_age"] = patient_age
        with pytest.raises(InvalidPatientEducationInputError):
            PatientEducationInput(**kwargs)  # type: ignore[arg-type]

    @pytest.mark.parametrize("patient_age", [0, 150])
    def test_boundary_patient_age_is_valid(self, patient_age: int) -> None:
        kwargs = self._valid_kwargs()
        kwargs["patient_age"] = patient_age
        input_dto = PatientEducationInput(**kwargs)  # type: ignore[arg-type]
        assert input_dto.patient_age == patient_age

    def test_patient_age_none_is_valid(self) -> None:
        input_dto = PatientEducationInput(**self._valid_kwargs())  # type: ignore[arg-type]
        assert input_dto.patient_age is None


class TestPatientEducationResult:
    def _base_kwargs(self) -> dict[str, object]:
        return {
            "patient_summary": "",
            "diagnosis_explanation": "",
            "medication_instructions": (),
            "home_care_plan": (),
            "lifestyle_advice": (),
            "diet_advice": (),
            "exercise_advice": (),
            "warning_signs": (),
            "emergency_instructions": (),
            "follow_up_plan": (),
            "patient_checklist": (),
            "confidence_score": None,
            "raw_text": "{}",
            "output_format": PatientEducationOutputFormat.JSON,
        }

    def test_fully_empty_result_is_empty(self) -> None:
        result = PatientEducationResult(**self._base_kwargs())  # type: ignore[arg-type]
        assert result.is_empty is True

    def test_non_blank_patient_summary_is_not_empty(self) -> None:
        kwargs = self._base_kwargs()
        kwargs["patient_summary"] = "You were seen today."
        result = PatientEducationResult(**kwargs)  # type: ignore[arg-type]
        assert result.is_empty is False

    def test_non_blank_diagnosis_explanation_is_not_empty(self) -> None:
        kwargs = self._base_kwargs()
        kwargs["diagnosis_explanation"] = "Your diagnosis means..."
        result = PatientEducationResult(**kwargs)  # type: ignore[arg-type]
        assert result.is_empty is False

    @pytest.mark.parametrize(
        "field_name",
        [
            "medication_instructions",
            "home_care_plan",
            "lifestyle_advice",
            "diet_advice",
            "exercise_advice",
            "warning_signs",
            "emergency_instructions",
            "follow_up_plan",
            "patient_checklist",
        ],
    )
    def test_non_empty_list_field_is_not_empty(self, field_name: str) -> None:
        kwargs = self._base_kwargs()
        kwargs[field_name] = ("something",)
        result = PatientEducationResult(**kwargs)  # type: ignore[arg-type]
        assert result.is_empty is False


class TestPatientEducationTemplateSet:
    def test_construction(self) -> None:
        template_set = PatientEducationTemplateSet(
            system_template_name="patient_education.adult.system",
            developer_template_name="patient_education.adult.developer",
            user_template_name="patient_education.adult.user",
            version=1,
        )
        assert template_set.version == 1


class TestGenerationSession:
    def test_construction_with_defaults(self) -> None:
        session = GenerationSession(
            generation_id=uuid4(),
            provider="mock",
            model="mock-model",
            education_setting="adult",
            language="en",
            status=EducationGenerationStatus.COMPLETED,
        )
        assert session.latency_ms == 0.0
        assert session.prompt_tokens == 0
        assert session.completion_tokens == 0
        assert session.total_tokens == 0
        assert session.estimated_cost_usd == 0.0
        assert isinstance(session.created_at, datetime)
        assert session.created_at.tzinfo is UTC

    def test_status_failed(self) -> None:
        session = GenerationSession(
            generation_id=uuid4(),
            provider="mock",
            model="mock-model",
            education_setting="adult",
            language="en",
            status=EducationGenerationStatus.FAILED,
        )
        assert session.status is EducationGenerationStatus.FAILED


class TestPatientEducationStreamChunk:
    def test_default_is_final_false(self) -> None:
        chunk = PatientEducationStreamChunk(delta="hello")
        assert chunk.is_final is False

    def test_is_final_true(self) -> None:
        chunk = PatientEducationStreamChunk(delta="", is_final=True)
        assert chunk.is_final is True
