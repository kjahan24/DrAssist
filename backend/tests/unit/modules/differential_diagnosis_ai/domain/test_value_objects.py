"""Unit tests for the AI Differential Diagnosis module's domain value
objects."""

from uuid import uuid4

import pytest

from app.modules.differential_diagnosis_ai.domain.enums import (
    ClinicalSetting,
    DifferentialOutputFormat,
    GenerationStatus,
    PatientSex,
    PregnancyStatus,
    UrgencyLevel,
)
from app.modules.differential_diagnosis_ai.domain.exceptions import InvalidClinicalEvidenceError
from app.modules.differential_diagnosis_ai.domain.value_objects import (
    DifferentialDiagnosisCandidate,
    DifferentialDiagnosisInput,
    DifferentialDiagnosisResult,
    DifferentialDiagnosisStreamChunk,
    DifferentialDiagnosisTemplateSet,
    GenerationSession,
)


def _evidence(**overrides: object) -> DifferentialDiagnosisInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Chest pain",
        "clinical_setting": ClinicalSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return DifferentialDiagnosisInput(**defaults)  # type: ignore[arg-type]


class TestDifferentialDiagnosisInput:
    def test_constructs_with_required_fields_only(self) -> None:
        evidence = _evidence()
        assert evidence.chief_complaint == "Chest pain"
        assert evidence.language == "en"
        assert evidence.visit_id is None
        assert evidence.symptoms == ()
        assert evidence.icd10_suggestions == ()
        assert evidence.prescription_suggestions == ()
        assert evidence.patient_age is None
        assert evidence.pregnancy_status is None
        assert evidence.output_format is DifferentialOutputFormat.JSON

    def test_accepts_the_full_set_of_optional_fields(self) -> None:
        visit_id = uuid4()
        evidence = _evidence(
            visit_id=visit_id,
            history_of_present_illness="Gradual onset over 2 hours",
            symptoms=("chest pain", "shortness of breath"),
            review_of_systems="Negative except as noted",
            physical_examination="Tachycardic, mild distress",
            vitals={"HR": "110"},
            laboratory_results=("Troponin: 0.02",),
            imaging_summary="CXR unremarkable",
            clinical_note="Full clinical note text",
            soap_note="Full SOAP note text",
            icd10_suggestions=("R07.9",),
            prescription_suggestions=("aspirin 81mg",),
            allergies=("penicillin",),
            medical_conditions=("hypertension",),
            patient_age=54,
            patient_sex=PatientSex.MALE,
            pregnancy_status=PregnancyStatus.NOT_APPLICABLE,
            visit_type="Outpatient",
            language="es",
            clinical_setting=ClinicalSetting.EMERGENCY,
            output_format=DifferentialOutputFormat.MARKDOWN,
        )
        assert evidence.visit_id == visit_id
        assert evidence.patient_age == 54
        assert evidence.patient_sex is PatientSex.MALE
        assert evidence.pregnancy_status is PregnancyStatus.NOT_APPLICABLE
        assert evidence.clinical_setting is ClinicalSetting.EMERGENCY
        assert evidence.output_format is DifferentialOutputFormat.MARKDOWN

    @pytest.mark.parametrize("chief_complaint", ["", "   "])
    def test_rejects_blank_chief_complaint(self, chief_complaint: str) -> None:
        with pytest.raises(InvalidClinicalEvidenceError):
            _evidence(chief_complaint=chief_complaint)

    @pytest.mark.parametrize("language", ["", "   "])
    def test_rejects_blank_language(self, language: str) -> None:
        with pytest.raises(InvalidClinicalEvidenceError):
            _evidence(language=language)

    @pytest.mark.parametrize("patient_age", [-1, 151, -100])
    def test_rejects_implausible_patient_age(self, patient_age: int) -> None:
        with pytest.raises(InvalidClinicalEvidenceError):
            _evidence(patient_age=patient_age)

    @pytest.mark.parametrize("patient_age", [0, 1, 150])
    def test_accepts_boundary_valid_ages(self, patient_age: int) -> None:
        evidence = _evidence(patient_age=patient_age)
        assert evidence.patient_age == patient_age

    def test_equality_is_by_value(self) -> None:
        organization_id = uuid4()
        patient_id = uuid4()
        a = _evidence(organization_id=organization_id, patient_id=patient_id)
        b = _evidence(organization_id=organization_id, patient_id=patient_id)
        assert a == b


class TestDifferentialDiagnosisCandidate:
    def _candidate(self, **overrides: object) -> DifferentialDiagnosisCandidate:
        defaults: dict[str, object] = {
            "disease_name": "Pneumonia",
            "icd10_code": "J18.9",
            "confidence_score": 0.7,
            "clinical_reasoning": "Consistent with fever and productive cough",
            "supporting_findings": ("fever", "productive cough"),
            "findings_against": ("no consolidation on exam",),
            "recommended_next_tests": ("chest x-ray",),
            "red_flag_indicators": (),
            "urgency_level": UrgencyLevel.URGENT,
        }
        defaults.update(overrides)
        return DifferentialDiagnosisCandidate(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_all_fields(self) -> None:
        candidate = self._candidate()
        assert candidate.disease_name == "Pneumonia"
        assert candidate.icd10_code == "J18.9"
        assert candidate.urgency_level is UrgencyLevel.URGENT

    def test_accepts_a_null_icd10_code(self) -> None:
        candidate = self._candidate(icd10_code=None)
        assert candidate.icd10_code is None

    def test_accepts_a_null_confidence_score(self) -> None:
        candidate = self._candidate(confidence_score=None)
        assert candidate.confidence_score is None

    def test_equality_is_by_value(self) -> None:
        a = self._candidate()
        b = self._candidate()
        assert a == b


class TestDifferentialDiagnosisResult:
    def _result(self, **overrides: object) -> DifferentialDiagnosisResult:
        defaults: dict[str, object] = {
            "candidates": (
                DifferentialDiagnosisCandidate(
                    disease_name="Pneumonia",
                    icd10_code="J18.9",
                    confidence_score=0.7,
                    clinical_reasoning="Reasoning A",
                    supporting_findings=(),
                    findings_against=(),
                    recommended_next_tests=(),
                    red_flag_indicators=(),
                    urgency_level=UrgencyLevel.URGENT,
                ),
                DifferentialDiagnosisCandidate(
                    disease_name="Bronchitis",
                    icd10_code=None,
                    confidence_score=0.4,
                    clinical_reasoning="Reasoning B",
                    supporting_findings=(),
                    findings_against=(),
                    recommended_next_tests=(),
                    red_flag_indicators=(),
                    urgency_level=UrgencyLevel.ROUTINE,
                ),
            ),
            "serious_diagnoses_not_to_miss": (),
            "suggested_investigations": (),
            "suggested_referrals": (),
            "raw_text": '{"candidates": []}',
            "output_format": DifferentialOutputFormat.JSON,
        }
        defaults.update(overrides)
        return DifferentialDiagnosisResult(**defaults)  # type: ignore[arg-type]

    def test_is_empty_is_false_when_populated(self) -> None:
        assert self._result().is_empty is False

    def test_is_empty_is_true_when_no_candidates(self) -> None:
        assert self._result(candidates=()).is_empty is True

    def test_most_likely_diagnosis_is_the_first_candidate(self) -> None:
        result = self._result()
        assert result.most_likely_diagnosis == "Pneumonia"

    def test_most_likely_diagnosis_is_none_when_empty(self) -> None:
        result = self._result(candidates=())
        assert result.most_likely_diagnosis is None


class TestDifferentialDiagnosisTemplateSet:
    def test_constructs_with_all_fields(self) -> None:
        template_set = DifferentialDiagnosisTemplateSet(
            system_template_name="differential_diagnosis_suggestion.outpatient.system",
            developer_template_name="differential_diagnosis_suggestion.outpatient.developer",
            user_template_name="differential_diagnosis_suggestion.outpatient.user",
            version=1,
        )
        assert template_set.version == 1
        assert (
            template_set.system_template_name
            == "differential_diagnosis_suggestion.outpatient.system"
        )


class TestGenerationSession:
    def _session(self, **overrides: object) -> GenerationSession:
        defaults: dict[str, object] = {
            "generation_id": uuid4(),
            "provider": "mock",
            "model": "mock-model",
            "clinical_setting": "outpatient",
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


class TestDifferentialDiagnosisStreamChunk:
    def test_defaults_is_final_to_false(self) -> None:
        chunk = DifferentialDiagnosisStreamChunk(delta="hello")
        assert chunk.is_final is False

    def test_accepts_is_final_true(self) -> None:
        chunk = DifferentialDiagnosisStreamChunk(delta="", is_final=True)
        assert chunk.is_final is True
