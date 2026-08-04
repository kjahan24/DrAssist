"""Unit tests for the AI Medical Reasoning Engine's domain value
objects."""

from uuid import uuid4

import pytest

from app.modules.medical_reasoning_ai.domain.enums import (
    EvidencePolarity,
    MedicalReasoningOutputFormat,
    PatientSex,
    PregnancyStatus,
    ReasoningSetting,
    ReasoningStatus,
    RedFlagPriority,
)
from app.modules.medical_reasoning_ai.domain.exceptions import InvalidMedicalReasoningInputError
from app.modules.medical_reasoning_ai.domain.value_objects import (
    EvidenceItem,
    GenerationSession,
    MedicalReasoningInput,
    MedicalReasoningResult,
    MedicalReasoningStreamChunk,
    MedicalReasoningTemplateSet,
    RedFlag,
)


def _evidence(**overrides: object) -> MedicalReasoningInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Chest pain",
        "reasoning_setting": ReasoningSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return MedicalReasoningInput(**defaults)  # type: ignore[arg-type]


class TestMedicalReasoningInput:
    def test_constructs_with_required_fields_only(self) -> None:
        evidence = _evidence()
        assert evidence.chief_complaint == "Chest pain"
        assert evidence.language == "en"
        assert evidence.visit_id is None
        assert evidence.symptoms == ()
        assert evidence.clinical_notes == ()
        assert evidence.soap_notes == ()
        assert evidence.differential_diagnoses == ()
        assert evidence.output_format is MedicalReasoningOutputFormat.JSON

    def test_accepts_the_full_set_of_optional_fields(self) -> None:
        visit_id = uuid4()
        evidence = _evidence(
            visit_id=visit_id,
            history_of_present_illness="Gradual onset",
            symptoms=("chest pain",),
            review_of_systems="Negative except as noted",
            physical_examination="Unremarkable",
            vitals={"HR": "110"},
            allergies=("penicillin",),
            medications=("lisinopril",),
            medical_conditions=("hypertension",),
            laboratory_results=("Troponin: 0.02",),
            imaging_summary="CXR unremarkable",
            clinical_notes=("Note text",),
            soap_notes=("SOAP text",),
            diagnoses=("Essential hypertension",),
            icd10_suggestions=("R07.9",),
            prescription_suggestions=("aspirin 81mg",),
            differential_diagnoses=("Pneumonia",),
            patient_age=54,
            patient_sex=PatientSex.MALE,
            pregnancy_status=PregnancyStatus.NOT_APPLICABLE,
            visit_type="Outpatient",
            language="es",
            reasoning_setting=ReasoningSetting.EMERGENCY,
            output_format=MedicalReasoningOutputFormat.MARKDOWN,
        )
        assert evidence.visit_id == visit_id
        assert evidence.patient_age == 54
        assert evidence.patient_sex is PatientSex.MALE
        assert evidence.pregnancy_status is PregnancyStatus.NOT_APPLICABLE
        assert evidence.reasoning_setting is ReasoningSetting.EMERGENCY
        assert evidence.output_format is MedicalReasoningOutputFormat.MARKDOWN

    @pytest.mark.parametrize("chief_complaint", ["", "   "])
    def test_rejects_blank_chief_complaint(self, chief_complaint: str) -> None:
        with pytest.raises(InvalidMedicalReasoningInputError):
            _evidence(chief_complaint=chief_complaint)

    @pytest.mark.parametrize("language", ["", "   "])
    def test_rejects_blank_language(self, language: str) -> None:
        with pytest.raises(InvalidMedicalReasoningInputError):
            _evidence(language=language)

    @pytest.mark.parametrize("patient_age", [-1, 151, -100])
    def test_rejects_implausible_patient_age(self, patient_age: int) -> None:
        with pytest.raises(InvalidMedicalReasoningInputError):
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


class TestEvidenceItem:
    def test_constructs_with_all_fields(self) -> None:
        item = EvidenceItem(
            description="Fever present", weight=0.7, polarity=EvidencePolarity.SUPPORTING
        )
        assert item.description == "Fever present"
        assert item.weight == 0.7
        assert item.polarity is EvidencePolarity.SUPPORTING

    def test_equality_is_by_value(self) -> None:
        a = EvidenceItem(description="x", weight=0.5, polarity=EvidencePolarity.SUPPORTING)
        b = EvidenceItem(description="x", weight=0.5, polarity=EvidencePolarity.SUPPORTING)
        assert a == b


class TestRedFlag:
    def test_constructs_with_all_fields(self) -> None:
        flag = RedFlag(description="Hypotension", priority=RedFlagPriority.CRITICAL)
        assert flag.description == "Hypotension"
        assert flag.priority is RedFlagPriority.CRITICAL


class TestMedicalReasoningResult:
    def _result(self, **overrides: object) -> MedicalReasoningResult:
        defaults: dict[str, object] = {
            "clinical_summary": "Patient presents with chest pain.",
            "evidence": (
                EvidenceItem(
                    description="Elevated troponin",
                    weight=0.8,
                    polarity=EvidencePolarity.SUPPORTING,
                ),
                EvidenceItem(
                    description="No ECG changes",
                    weight=0.4,
                    polarity=EvidencePolarity.CONTRADICTING,
                ),
            ),
            "missing_information": (),
            "clinical_confidence": 0.7,
            "diagnostic_confidence": 0.6,
            "therapeutic_confidence": 0.5,
            "risk_factors": (),
            "red_flags": (),
            "suggested_next_questions": (),
            "suggested_investigations": (),
            "suggested_monitoring": (),
            "clinical_justification": "Grounded in the elevated troponin.",
            "raw_text": "{}",
            "output_format": MedicalReasoningOutputFormat.JSON,
        }
        defaults.update(overrides)
        return MedicalReasoningResult(**defaults)  # type: ignore[arg-type]

    def test_supporting_evidence_filters_by_polarity(self) -> None:
        result = self._result()
        assert len(result.supporting_evidence) == 1
        assert result.supporting_evidence[0].description == "Elevated troponin"

    def test_contradicting_evidence_filters_by_polarity(self) -> None:
        result = self._result()
        assert len(result.contradicting_evidence) == 1
        assert result.contradicting_evidence[0].description == "No ECG changes"

    def test_is_empty_is_false_when_populated(self) -> None:
        assert self._result().is_empty is False

    def test_is_empty_is_true_when_fully_vacuous(self) -> None:
        result = self._result(
            clinical_summary="",
            evidence=(),
            risk_factors=(),
            red_flags=(),
            suggested_next_questions=(),
            suggested_investigations=(),
            suggested_monitoring=(),
            clinical_justification="",
        )
        assert result.is_empty is True

    def test_is_empty_is_false_when_only_summary_present(self) -> None:
        result = self._result(
            evidence=(),
            risk_factors=(),
            red_flags=(),
            suggested_next_questions=(),
            suggested_investigations=(),
            suggested_monitoring=(),
            clinical_justification="",
        )
        assert result.is_empty is False


class TestMedicalReasoningTemplateSet:
    def test_constructs_with_all_fields(self) -> None:
        template_set = MedicalReasoningTemplateSet(
            system_template_name="medical_reasoning.outpatient.system",
            developer_template_name="medical_reasoning.outpatient.developer",
            user_template_name="medical_reasoning.outpatient.user",
            version=1,
        )
        assert template_set.version == 1
        assert template_set.system_template_name == "medical_reasoning.outpatient.system"


class TestGenerationSession:
    def _session(self, **overrides: object) -> GenerationSession:
        defaults: dict[str, object] = {
            "generation_id": uuid4(),
            "provider": "mock",
            "model": "mock-model",
            "reasoning_setting": "outpatient",
            "language": "en",
            "status": ReasoningStatus.COMPLETED,
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


class TestMedicalReasoningStreamChunk:
    def test_defaults_is_final_to_false(self) -> None:
        chunk = MedicalReasoningStreamChunk(delta="hello")
        assert chunk.is_final is False

    def test_accepts_is_final_true(self) -> None:
        chunk = MedicalReasoningStreamChunk(delta="", is_final=True)
        assert chunk.is_final is True
