"""In-memory test doubles for the twelve peer AI modules' own public
ports — one small fake facade per orchestrated `WorkflowModule`, used by
this package's own adapter tests to verify each adapter's own
translation logic (generic bundle -> peer's own strongly-typed input;
peer's own result -> `WorkflowStepResult`) without a real AI Foundation
call.

Every fake here imports **only** from its own peer module's `public/`
package — never `.domain` — the same module-independence discipline
`app.modules.ai_orchestrator`'s own production adapters follow (see
`app/modules/ai_orchestrator/infrastructure/module_adapters/__init__.py`'s
own module docstring). Every peer module's own `public/dto.py` re-exports
`GenerationSession` itself, but most do **not** re-export the internal
"generation status" enum that field's own `status` needs (only
`app.modules.patient_education_ai` happens to) — rather than reach into
eleven different peer modules' own `.domain.enums` just for one status
value, every `GenerationSession` constructed below passes a plain
string (`"completed"`) for `status` instead, via the same
`dict[str, object]` splat + `# type: ignore[arg-type]` pattern every
prior AI module's own `application/fakes.py::make_result`/`make_input`
factory already establishes for itself — none of these value objects
perform runtime validation on construction (no `__post_init__` at all),
so a plain string is functionally identical and statically silenced the
same established way.
"""

from collections.abc import AsyncIterator
from uuid import uuid4

from app.modules.clinical_note_ai.public.dto import (
    ClinicalEncounterInput,
    ClinicalNote,
    ClinicalNoteOutputFormat,
    ClinicalNoteStreamChunk,
    GeneratedClinicalNote,
    ValidationResultDTO,
)
from app.modules.clinical_note_ai.public.dto import (
    GenerationSession as ClinicalNoteGenerationSession,
)
from app.modules.clinical_note_ai.public.interfaces import ClinicalNoteAIPort
from app.modules.differential_diagnosis_ai.public.dto import (
    ClinicalEvidenceValidationResultDTO,
    DifferentialDiagnosisInput,
    DifferentialDiagnosisResult,
    DifferentialDiagnosisStreamChunk,
    DifferentialOutputFormat,
    GeneratedDifferentialDiagnosis,
)
from app.modules.differential_diagnosis_ai.public.dto import (
    GenerationSession as DifferentialDiagnosisGenerationSession,
)
from app.modules.differential_diagnosis_ai.public.interfaces import DifferentialDiagnosisAIPort
from app.modules.drug_interaction_ai.public.dto import (
    DrugInteractionAnalysisInput,
    DrugInteractionAnalysisResult,
    DrugInteractionOutputFormat,
    DrugInteractionStreamChunk,
    GeneratedDrugInteractionAnalysis,
)
from app.modules.drug_interaction_ai.public.dto import (
    GenerationSession as DrugInteractionGenerationSession,
)
from app.modules.drug_interaction_ai.public.interfaces import DrugInteractionAIPort
from app.modules.icd10_ai.public.dto import (
    ClinicalContextValidationResultDTO,
    GeneratedICD10Suggestions,
    ICD10CodingInput,
    ICD10OutputFormat,
    ICD10StreamChunk,
    ICD10SuggestionSet,
)
from app.modules.icd10_ai.public.dto import (
    GenerationSession as ICD10GenerationSession,
)
from app.modules.icd10_ai.public.interfaces import ICD10AIPort
from app.modules.lab_interpretation_ai.public.dto import (
    GeneratedLabInterpretation,
    LabInterpretationInput,
    LabInterpretationOutputFormat,
    LabInterpretationResult,
    LabInterpretationStreamChunk,
)
from app.modules.lab_interpretation_ai.public.dto import (
    GenerationSession as LabInterpretationGenerationSession,
)
from app.modules.lab_interpretation_ai.public.interfaces import LabInterpretationAIPort
from app.modules.medical_reasoning_ai.public.dto import (
    EvidenceItem,
    GeneratedMedicalReasoning,
    MedicalReasoningInput,
    MedicalReasoningOutputFormat,
    MedicalReasoningResult,
    MedicalReasoningStreamChunk,
)
from app.modules.medical_reasoning_ai.public.dto import (
    GenerationSession as MedicalReasoningGenerationSession,
)
from app.modules.medical_reasoning_ai.public.interfaces import MedicalReasoningAIPort
from app.modules.pathology_interpretation_ai.public.dto import (
    GeneratedPathologyInterpretation,
    PathologyFinding,
    PathologyInterpretationInput,
    PathologyInterpretationResult,
    PathologyInterpretationStreamChunk,
    PathologyOutputFormat,
)
from app.modules.pathology_interpretation_ai.public.dto import (
    GenerationSession as PathologyGenerationSession,
)
from app.modules.pathology_interpretation_ai.public.interfaces import (
    PathologyInterpretationAIPort,
)
from app.modules.patient_education_ai.public.dto import (
    EducationGenerationStatus,
    GeneratedPatientEducation,
    PatientEducationInput,
    PatientEducationOutputFormat,
    PatientEducationResult,
    PatientEducationStreamChunk,
)
from app.modules.patient_education_ai.public.dto import (
    GenerationSession as PatientEducationGenerationSession,
)
from app.modules.patient_education_ai.public.interfaces import PatientEducationAIPort
from app.modules.prescription_ai.public.dto import (
    GeneratedPrescriptionSuggestions,
    MedicationSafetyFinding,
    PrescriptionContextInput,
    PrescriptionContextValidationResultDTO,
    PrescriptionOutputFormat,
    PrescriptionStreamChunk,
    PrescriptionSuggestionSet,
)
from app.modules.prescription_ai.public.dto import (
    GenerationSession as PrescriptionGenerationSession,
)
from app.modules.prescription_ai.public.interfaces import PrescriptionAIPort
from app.modules.radiology_interpretation_ai.public.dto import (
    GeneratedRadiologyInterpretation,
    RadiologyFinding,
    RadiologyInterpretationInput,
    RadiologyInterpretationResult,
    RadiologyInterpretationStreamChunk,
    RadiologyOutputFormat,
)
from app.modules.radiology_interpretation_ai.public.dto import (
    GenerationSession as RadiologyGenerationSession,
)
from app.modules.radiology_interpretation_ai.public.interfaces import (
    RadiologyInterpretationAIPort,
)
from app.modules.risk_stratification_ai.public.dto import (
    GeneratedRiskStratification,
    OverallRiskLevel,
    RiskStratificationInput,
    RiskStratificationOutputFormat,
    RiskStratificationResult,
    RiskStratificationStreamChunk,
)
from app.modules.risk_stratification_ai.public.dto import (
    GenerationSession as RiskStratificationGenerationSession,
)
from app.modules.risk_stratification_ai.public.interfaces import RiskStratificationAIPort
from app.modules.soap_note_ai.public.dto import (
    GeneratedSOAPNote,
    SOAPEncounterInput,
    SOAPNote,
    SOAPNoteOutputFormat,
    SOAPNoteStreamChunk,
    SOAPValidationResultDTO,
)
from app.modules.soap_note_ai.public.dto import (
    GenerationSession as SOAPNoteGenerationSession,
)
from app.modules.soap_note_ai.public.interfaces import SOAPNoteAIPort

_NOT_EXERCISED = "not exercised by ai_orchestrator's own adapter tests"


def _session_kwargs(**overrides: object) -> dict[str, object]:
    defaults: dict[str, object] = {
        "generation_id": uuid4(),
        "provider": "mock",
        "model": "mock-model",
        "language": "en",
        "status": "completed",
        "latency_ms": 1.0,
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "estimated_cost_usd": 0.0001,
    }
    defaults.update(overrides)
    return defaults


# --------------------------------------------------------------------------
# clinical_note_ai
# --------------------------------------------------------------------------


def make_generated_clinical_note(
    *, raw_text: str = "clinical note raw text"
) -> GeneratedClinicalNote:
    return GeneratedClinicalNote(
        note=ClinicalNote(
            sections=(), raw_text=raw_text, output_format=ClinicalNoteOutputFormat.JSON
        ),
        session=ClinicalNoteGenerationSession(**_session_kwargs(note_style="outpatient")),  # type: ignore[arg-type]
    )


class FakeClinicalNoteAIPort(ClinicalNoteAIPort):
    def __init__(self, *, generated: GeneratedClinicalNote | None = None) -> None:
        self._generated = generated or make_generated_clinical_note()
        self.received: list[ClinicalEncounterInput] = []

    async def generate_note(self, encounter: ClinicalEncounterInput) -> GeneratedClinicalNote:
        self.received.append(encounter)
        return self._generated

    def stream_generate_note(
        self, encounter: ClinicalEncounterInput
    ) -> AsyncIterator[ClinicalNoteStreamChunk]:
        raise NotImplementedError(_NOT_EXERCISED)

    async def render_note(
        self, note: ClinicalNote, *, target_format: ClinicalNoteOutputFormat
    ) -> str:
        raise NotImplementedError(_NOT_EXERCISED)

    async def validate_input(self, encounter: ClinicalEncounterInput) -> ValidationResultDTO:
        raise NotImplementedError(_NOT_EXERCISED)


# --------------------------------------------------------------------------
# soap_note_ai
# --------------------------------------------------------------------------


def make_generated_soap_note(*, raw_text: str = "soap note raw text") -> GeneratedSOAPNote:
    return GeneratedSOAPNote(
        note=SOAPNote(sections=(), raw_text=raw_text, output_format=SOAPNoteOutputFormat.JSON),
        session=SOAPNoteGenerationSession(**_session_kwargs(soap_style="standard")),  # type: ignore[arg-type]
    )


class FakeSOAPNoteAIPort(SOAPNoteAIPort):
    def __init__(self, *, generated: GeneratedSOAPNote | None = None) -> None:
        self._generated = generated or make_generated_soap_note()
        self.received: list[SOAPEncounterInput] = []

    async def generate_note(self, encounter: SOAPEncounterInput) -> GeneratedSOAPNote:
        self.received.append(encounter)
        return self._generated

    def stream_generate_note(
        self, encounter: SOAPEncounterInput
    ) -> AsyncIterator[SOAPNoteStreamChunk]:
        raise NotImplementedError(_NOT_EXERCISED)

    async def render_note(self, note: SOAPNote, *, target_format: SOAPNoteOutputFormat) -> str:
        raise NotImplementedError(_NOT_EXERCISED)

    async def validate_input(self, encounter: SOAPEncounterInput) -> SOAPValidationResultDTO:
        raise NotImplementedError(_NOT_EXERCISED)


# --------------------------------------------------------------------------
# icd10_ai
# --------------------------------------------------------------------------


def make_generated_icd10_suggestions(
    *, raw_text: str = "icd10 raw text"
) -> GeneratedICD10Suggestions:
    return GeneratedICD10Suggestions(
        suggestions=ICD10SuggestionSet(
            suggestions=(), raw_text=raw_text, output_format=ICD10OutputFormat.JSON
        ),
        session=ICD10GenerationSession(**_session_kwargs(coding_setting="outpatient")),  # type: ignore[arg-type]
    )


class FakeICD10AIPort(ICD10AIPort):
    def __init__(self, *, generated: GeneratedICD10Suggestions | None = None) -> None:
        self._generated = generated or make_generated_icd10_suggestions()
        self.received: list[ICD10CodingInput] = []

    async def generate_suggestions(
        self, coding_input: ICD10CodingInput
    ) -> GeneratedICD10Suggestions:
        self.received.append(coding_input)
        return self._generated

    def stream_generate_suggestions(
        self, coding_input: ICD10CodingInput
    ) -> AsyncIterator[ICD10StreamChunk]:
        raise NotImplementedError(_NOT_EXERCISED)

    async def rank_suggestions(self, suggestion_set: ICD10SuggestionSet) -> ICD10SuggestionSet:
        raise NotImplementedError(_NOT_EXERCISED)

    async def render_suggestions(
        self, suggestion_set: ICD10SuggestionSet, *, target_format: ICD10OutputFormat
    ) -> str:
        raise NotImplementedError(_NOT_EXERCISED)

    async def validate_context(
        self, coding_input: ICD10CodingInput
    ) -> ClinicalContextValidationResultDTO:
        raise NotImplementedError(_NOT_EXERCISED)


# --------------------------------------------------------------------------
# prescription_ai
# --------------------------------------------------------------------------


def make_generated_prescription_suggestions(
    *, raw_text: str = "prescription raw text"
) -> GeneratedPrescriptionSuggestions:
    session_kwargs = _session_kwargs(prescribing_setting="outpatient")
    return GeneratedPrescriptionSuggestions(
        suggestions=PrescriptionSuggestionSet(
            medications=(),
            safety_findings=(),
            monitoring_recommendations=(),
            follow_up_recommendations=(),
            raw_text=raw_text,
            output_format=PrescriptionOutputFormat.JSON,
        ),
        session=PrescriptionGenerationSession(**session_kwargs),  # type: ignore[arg-type]
    )


class FakePrescriptionAIPort(PrescriptionAIPort):
    def __init__(self, *, generated: GeneratedPrescriptionSuggestions | None = None) -> None:
        self._generated = generated or make_generated_prescription_suggestions()
        self.received: list[PrescriptionContextInput] = []

    async def generate_suggestion(
        self, context: PrescriptionContextInput
    ) -> GeneratedPrescriptionSuggestions:
        self.received.append(context)
        return self._generated

    def stream_generate_suggestion(
        self, context: PrescriptionContextInput
    ) -> AsyncIterator[PrescriptionStreamChunk]:
        raise NotImplementedError(_NOT_EXERCISED)

    async def analyze_medication_safety(
        self,
        suggestion_set: PrescriptionSuggestionSet,
        *,
        existing_medications: tuple[str, ...] = (),
        allergies: tuple[str, ...] = (),
    ) -> tuple[MedicationSafetyFinding, ...]:
        raise NotImplementedError(_NOT_EXERCISED)

    async def render_suggestions(
        self, suggestion_set: PrescriptionSuggestionSet, *, target_format: PrescriptionOutputFormat
    ) -> str:
        raise NotImplementedError(_NOT_EXERCISED)

    async def validate_context(
        self, context: PrescriptionContextInput
    ) -> PrescriptionContextValidationResultDTO:
        raise NotImplementedError(_NOT_EXERCISED)


# --------------------------------------------------------------------------
# differential_diagnosis_ai
# --------------------------------------------------------------------------


def make_generated_differential_diagnosis(
    *, raw_text: str = "differential diagnosis raw text"
) -> GeneratedDifferentialDiagnosis:
    session_kwargs = _session_kwargs(clinical_setting="outpatient")
    return GeneratedDifferentialDiagnosis(
        result=DifferentialDiagnosisResult(
            candidates=(),
            serious_diagnoses_not_to_miss=(),
            suggested_investigations=(),
            suggested_referrals=(),
            raw_text=raw_text,
            output_format=DifferentialOutputFormat.JSON,
        ),
        session=DifferentialDiagnosisGenerationSession(**session_kwargs),  # type: ignore[arg-type]
    )


class FakeDifferentialDiagnosisAIPort(DifferentialDiagnosisAIPort):
    def __init__(self, *, generated: GeneratedDifferentialDiagnosis | None = None) -> None:
        self._generated = generated or make_generated_differential_diagnosis()
        self.received: list[DifferentialDiagnosisInput] = []

    async def generate_differential_diagnosis(
        self, evidence: DifferentialDiagnosisInput
    ) -> GeneratedDifferentialDiagnosis:
        self.received.append(evidence)
        return self._generated

    def stream_generate_differential_diagnosis(
        self, evidence: DifferentialDiagnosisInput
    ) -> AsyncIterator[DifferentialDiagnosisStreamChunk]:
        raise NotImplementedError(_NOT_EXERCISED)

    async def rank_result(self, result: DifferentialDiagnosisResult) -> DifferentialDiagnosisResult:
        raise NotImplementedError(_NOT_EXERCISED)

    async def render_result(
        self, result: DifferentialDiagnosisResult, *, target_format: DifferentialOutputFormat
    ) -> str:
        raise NotImplementedError(_NOT_EXERCISED)

    async def validate_evidence(
        self, evidence: DifferentialDiagnosisInput
    ) -> ClinicalEvidenceValidationResultDTO:
        raise NotImplementedError(_NOT_EXERCISED)


# --------------------------------------------------------------------------
# medical_reasoning_ai
# --------------------------------------------------------------------------


def make_generated_medical_reasoning(
    *,
    raw_text: str = "medical reasoning raw text",
    clinical_confidence: float | None = 0.7,
    diagnostic_confidence: float | None = 0.8,
    therapeutic_confidence: float | None = 0.9,
) -> GeneratedMedicalReasoning:
    session_kwargs = _session_kwargs(reasoning_setting="outpatient")
    return GeneratedMedicalReasoning(
        result=MedicalReasoningResult(
            clinical_summary="summary",
            evidence=(),
            missing_information=(),
            clinical_confidence=clinical_confidence,
            diagnostic_confidence=diagnostic_confidence,
            therapeutic_confidence=therapeutic_confidence,
            risk_factors=(),
            red_flags=(),
            suggested_next_questions=(),
            suggested_investigations=(),
            suggested_monitoring=(),
            clinical_justification="justification",
            raw_text=raw_text,
            output_format=MedicalReasoningOutputFormat.JSON,
        ),
        session=MedicalReasoningGenerationSession(**session_kwargs),  # type: ignore[arg-type]
    )


class FakeMedicalReasoningAIPort(MedicalReasoningAIPort):
    def __init__(self, *, generated: GeneratedMedicalReasoning | None = None) -> None:
        self._generated = generated or make_generated_medical_reasoning()
        self.received: list[MedicalReasoningInput] = []

    async def generate_reasoning(
        self, evidence: MedicalReasoningInput
    ) -> GeneratedMedicalReasoning:
        self.received.append(evidence)
        return self._generated

    def stream_generate_reasoning(
        self, evidence: MedicalReasoningInput
    ) -> AsyncIterator[MedicalReasoningStreamChunk]:
        raise NotImplementedError(_NOT_EXERCISED)

    async def render_result(
        self, result: MedicalReasoningResult, *, target_format: MedicalReasoningOutputFormat
    ) -> str:
        raise NotImplementedError(_NOT_EXERCISED)

    def weight_evidence(self, items: tuple[EvidenceItem, ...]) -> tuple[EvidenceItem, ...]:
        raise NotImplementedError(_NOT_EXERCISED)

    def score_confidence(
        self,
        *,
        ai_reported: float | None,
        supporting_count: int,
        contradicting_count: int,
        missing_information_count: int,
    ) -> float:
        raise NotImplementedError(_NOT_EXERCISED)


# --------------------------------------------------------------------------
# lab_interpretation_ai
# --------------------------------------------------------------------------


def make_generated_lab_interpretation(
    *, raw_text: str = "lab interpretation raw text", confidence_score: float | None = 0.75
) -> GeneratedLabInterpretation:
    session_kwargs = _session_kwargs(lab_setting="outpatient")
    return GeneratedLabInterpretation(
        result=LabInterpretationResult(
            overall_interpretation="interpretation",
            findings=(),
            clinical_significance="significance",
            supporting_evidence=(),
            potential_causes=(),
            suggested_follow_up_tests=(),
            monitoring_recommendations=(),
            red_flag_warnings=(),
            confidence_score=confidence_score,
            raw_text=raw_text,
            output_format=LabInterpretationOutputFormat.JSON,
        ),
        session=LabInterpretationGenerationSession(**session_kwargs),  # type: ignore[arg-type]
    )


class FakeLabInterpretationAIPort(LabInterpretationAIPort):
    def __init__(self, *, generated: GeneratedLabInterpretation | None = None) -> None:
        self._generated = generated or make_generated_lab_interpretation()
        self.received: list[LabInterpretationInput] = []

    async def generate_interpretation(
        self, input_dto: LabInterpretationInput
    ) -> GeneratedLabInterpretation:
        self.received.append(input_dto)
        return self._generated

    def stream_generate_interpretation(
        self, input_dto: LabInterpretationInput
    ) -> AsyncIterator[LabInterpretationStreamChunk]:
        raise NotImplementedError(_NOT_EXERCISED)

    async def render_result(
        self, result: LabInterpretationResult, *, target_format: LabInterpretationOutputFormat
    ) -> str:
        raise NotImplementedError(_NOT_EXERCISED)


# --------------------------------------------------------------------------
# radiology_interpretation_ai
# --------------------------------------------------------------------------


def make_generated_radiology_interpretation(
    *, raw_text: str = "radiology raw text", confidence_score: float | None = 0.65
) -> GeneratedRadiologyInterpretation:
    session_kwargs = _session_kwargs(radiology_setting="outpatient", examination_type="general")
    return GeneratedRadiologyInterpretation(
        result=RadiologyInterpretationResult(
            examination_summary="summary",
            findings=(),
            clinical_significance="significance",
            differential_imaging_considerations=(),
            suggested_follow_up_imaging=(),
            suggested_specialist_referral=(),
            red_flag_warnings=(),
            confidence_score=confidence_score,
            clinical_reasoning="reasoning",
            raw_text=raw_text,
            output_format=RadiologyOutputFormat.JSON,
        ),
        session=RadiologyGenerationSession(**session_kwargs),  # type: ignore[arg-type]
    )


class FakeRadiologyInterpretationAIPort(RadiologyInterpretationAIPort):
    def __init__(self, *, generated: GeneratedRadiologyInterpretation | None = None) -> None:
        self._generated = generated or make_generated_radiology_interpretation()
        self.received: list[RadiologyInterpretationInput] = []

    async def generate_interpretation(
        self, input_dto: RadiologyInterpretationInput
    ) -> GeneratedRadiologyInterpretation:
        self.received.append(input_dto)
        return self._generated

    def stream_generate_interpretation(
        self, input_dto: RadiologyInterpretationInput
    ) -> AsyncIterator[RadiologyInterpretationStreamChunk]:
        raise NotImplementedError(_NOT_EXERCISED)

    async def render_result(
        self, result: RadiologyInterpretationResult, *, target_format: RadiologyOutputFormat
    ) -> str:
        raise NotImplementedError(_NOT_EXERCISED)

    def extract_candidate_findings(self, report_text: str) -> tuple[RadiologyFinding, ...]:
        raise NotImplementedError(_NOT_EXERCISED)


# --------------------------------------------------------------------------
# pathology_interpretation_ai
# --------------------------------------------------------------------------


def make_generated_pathology_interpretation(
    *, raw_text: str = "pathology raw text", confidence_score: float | None = 0.55
) -> GeneratedPathologyInterpretation:
    session_kwargs = _session_kwargs(
        pathology_setting="outpatient", examination_type="histopathology"
    )
    return GeneratedPathologyInterpretation(
        result=PathologyInterpretationResult(
            pathology_summary="summary",
            key_findings=(),
            microscopic_findings=(),
            final_impression="impression",
            clinical_significance="significance",
            correlation_recommendations=(),
            suggested_follow_up=(),
            suggested_specialist_referral=(),
            red_flag_warnings=(),
            confidence_score=confidence_score,
            clinical_reasoning="reasoning",
            raw_text=raw_text,
            output_format=PathologyOutputFormat.JSON,
        ),
        session=PathologyGenerationSession(**session_kwargs),  # type: ignore[arg-type]
    )


class FakePathologyInterpretationAIPort(PathologyInterpretationAIPort):
    def __init__(self, *, generated: GeneratedPathologyInterpretation | None = None) -> None:
        self._generated = generated or make_generated_pathology_interpretation()
        self.received: list[PathologyInterpretationInput] = []

    async def generate_interpretation(
        self, input_dto: PathologyInterpretationInput
    ) -> GeneratedPathologyInterpretation:
        self.received.append(input_dto)
        return self._generated

    def stream_generate_interpretation(
        self, input_dto: PathologyInterpretationInput
    ) -> AsyncIterator[PathologyInterpretationStreamChunk]:
        raise NotImplementedError(_NOT_EXERCISED)

    async def render_result(
        self, result: PathologyInterpretationResult, *, target_format: PathologyOutputFormat
    ) -> str:
        raise NotImplementedError(_NOT_EXERCISED)

    def extract_candidate_findings(self, report_text: str) -> tuple[PathologyFinding, ...]:
        raise NotImplementedError(_NOT_EXERCISED)


# --------------------------------------------------------------------------
# drug_interaction_ai
# --------------------------------------------------------------------------


def make_generated_drug_interaction_analysis(
    *, raw_text: str = "drug interaction raw text", confidence_score: float | None = 0.85
) -> GeneratedDrugInteractionAnalysis:
    session_kwargs = _session_kwargs(medication_setting="outpatient")
    return GeneratedDrugInteractionAnalysis(
        result=DrugInteractionAnalysisResult(
            safety_summary="summary",
            interactions=(),
            contraindications=(),
            warnings=(),
            monitoring_recommendations=(),
            dose_adjustment_suggestions=(),
            alternative_medication_suggestions=(),
            patient_counseling_points=(),
            clinical_reasoning="reasoning",
            confidence_score=confidence_score,
            raw_text=raw_text,
            output_format=DrugInteractionOutputFormat.JSON,
        ),
        session=DrugInteractionGenerationSession(**session_kwargs),  # type: ignore[arg-type]
    )


class FakeDrugInteractionAIPort(DrugInteractionAIPort):
    def __init__(self, *, generated: GeneratedDrugInteractionAnalysis | None = None) -> None:
        self._generated = generated or make_generated_drug_interaction_analysis()
        self.received: list[DrugInteractionAnalysisInput] = []

    async def analyze_medication_safety(
        self, input_dto: DrugInteractionAnalysisInput
    ) -> GeneratedDrugInteractionAnalysis:
        self.received.append(input_dto)
        return self._generated

    def stream_analyze_medication_safety(
        self, input_dto: DrugInteractionAnalysisInput
    ) -> AsyncIterator[DrugInteractionStreamChunk]:
        raise NotImplementedError(_NOT_EXERCISED)

    async def render_result(
        self, result: DrugInteractionAnalysisResult, *, target_format: DrugInteractionOutputFormat
    ) -> str:
        raise NotImplementedError(_NOT_EXERCISED)


# --------------------------------------------------------------------------
# risk_stratification_ai
# --------------------------------------------------------------------------


def make_generated_risk_stratification(
    *, raw_text: str = "risk stratification raw text", confidence_score: float | None = 0.6
) -> GeneratedRiskStratification:
    session_kwargs = _session_kwargs(risk_setting="outpatient")
    return GeneratedRiskStratification(
        result=RiskStratificationResult(
            overall_risk_level=OverallRiskLevel.LOW,
            risk_scores=(),
            early_warning_indicators=(),
            recommended_monitoring=(),
            suggested_escalation=(),
            suggested_follow_up=(),
            red_flag_alerts=(),
            clinical_reasoning="reasoning",
            confidence_score=confidence_score,
            raw_text=raw_text,
            output_format=RiskStratificationOutputFormat.JSON,
        ),
        session=RiskStratificationGenerationSession(**session_kwargs),  # type: ignore[arg-type]
    )


class FakeRiskStratificationAIPort(RiskStratificationAIPort):
    def __init__(self, *, generated: GeneratedRiskStratification | None = None) -> None:
        self._generated = generated or make_generated_risk_stratification()
        self.received: list[RiskStratificationInput] = []

    async def analyze_patient_risk(
        self, input_dto: RiskStratificationInput
    ) -> GeneratedRiskStratification:
        self.received.append(input_dto)
        return self._generated

    def stream_analyze_patient_risk(
        self, input_dto: RiskStratificationInput
    ) -> AsyncIterator[RiskStratificationStreamChunk]:
        raise NotImplementedError(_NOT_EXERCISED)

    async def render_result(
        self,
        result: RiskStratificationResult,
        *,
        target_format: RiskStratificationOutputFormat,
    ) -> str:
        raise NotImplementedError(_NOT_EXERCISED)


# --------------------------------------------------------------------------
# patient_education_ai
# --------------------------------------------------------------------------


def make_generated_patient_education(
    *, raw_text: str = "patient education raw text", confidence_score: float | None = 0.7
) -> GeneratedPatientEducation:
    return GeneratedPatientEducation(
        result=PatientEducationResult(
            patient_summary="summary",
            diagnosis_explanation="explanation",
            medication_instructions=(),
            home_care_plan=(),
            lifestyle_advice=(),
            diet_advice=(),
            exercise_advice=(),
            warning_signs=(),
            emergency_instructions=(),
            follow_up_plan=(),
            patient_checklist=(),
            confidence_score=confidence_score,
            raw_text=raw_text,
            output_format=PatientEducationOutputFormat.JSON,
        ),
        session=PatientEducationGenerationSession(
            generation_id=uuid4(),
            provider="mock",
            model="mock-model",
            education_setting="adult",
            language="en",
            status=EducationGenerationStatus.COMPLETED,
        ),
    )


class FakePatientEducationAIPort(PatientEducationAIPort):
    def __init__(self, *, generated: GeneratedPatientEducation | None = None) -> None:
        self._generated = generated or make_generated_patient_education()
        self.received: list[PatientEducationInput] = []

    async def generate_patient_education(
        self, input_dto: PatientEducationInput
    ) -> GeneratedPatientEducation:
        self.received.append(input_dto)
        return self._generated

    def stream_generate_patient_education(
        self, input_dto: PatientEducationInput
    ) -> AsyncIterator[PatientEducationStreamChunk]:
        raise NotImplementedError(_NOT_EXERCISED)

    async def render_result(
        self,
        result: PatientEducationResult,
        *,
        target_format: PatientEducationOutputFormat,
    ) -> str:
        raise NotImplementedError(_NOT_EXERCISED)
