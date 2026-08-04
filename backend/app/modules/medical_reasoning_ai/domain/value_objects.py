"""Value objects for the AI Medical Reasoning Engine's domain.

None of these reference another module's `domain`/`application`/
`infrastructure` type — every cross-module identity (organization,
patient, visit) is a plain `UUID`, and clinical content (chief complaint,
HPI, symptoms, ROS, physical exam, vitals, allergies, medications,
medical conditions, laboratory results, imaging summary, clinical/SOAP
notes, diagnoses, ICD-10 suggestions, prescription suggestions,
differential diagnoses) is exactly what this task's own INPUT
specification calls for: values the caller supplies directly, not
records looked up from the Clinical Copilot/Clinical Note AI/SOAP Note
AI/ICD-10 AI/Prescription AI/Differential Diagnosis AI modules. This
module never queries another module's public port — its entire input is
self-contained clinical evidence, the same design
`app.modules.differential_diagnosis_ai.domain.value_objects` establishes
for itself (see that module's own module docstring for the full
reasoning, which applies identically here — and see `container.py`'s own
scope note for why this holds even though this task explicitly frames
this module as the reasoning layer *for* those other modules).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

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
from app.shared.domain.value_object import ValueObject

_MAX_PLAUSIBLE_AGE = 150


@dataclass(frozen=True, slots=True)
class MedicalReasoningInput(ValueObject):
    organization_id: UUID
    patient_id: UUID
    chief_complaint: str
    reasoning_setting: ReasoningSetting
    language: str = "en"
    visit_id: UUID | None = None
    history_of_present_illness: str | None = None
    symptoms: tuple[str, ...] = ()
    review_of_systems: str | None = None
    physical_examination: str | None = None
    vitals: Mapping[str, str] = field(default_factory=dict)
    allergies: tuple[str, ...] = ()
    medications: tuple[str, ...] = ()
    medical_conditions: tuple[str, ...] = ()
    laboratory_results: tuple[str, ...] = ()
    imaging_summary: str | None = None
    clinical_notes: tuple[str, ...] = ()
    soap_notes: tuple[str, ...] = ()
    diagnoses: tuple[str, ...] = ()
    icd10_suggestions: tuple[str, ...] = ()
    prescription_suggestions: tuple[str, ...] = ()
    differential_diagnoses: tuple[str, ...] = ()
    patient_age: int | None = None
    patient_sex: PatientSex | None = None
    pregnancy_status: PregnancyStatus | None = None
    visit_type: str | None = None
    output_format: MedicalReasoningOutputFormat = MedicalReasoningOutputFormat.JSON

    def __post_init__(self) -> None:
        if not self.chief_complaint.strip():
            raise InvalidMedicalReasoningInputError("chief_complaint must not be blank")
        if not self.language.strip():
            raise InvalidMedicalReasoningInputError("language must not be blank")
        if self.patient_age is not None and not (0 <= self.patient_age <= _MAX_PLAUSIBLE_AGE):
            raise InvalidMedicalReasoningInputError(
                f"patient_age must be between 0 and {_MAX_PLAUSIBLE_AGE} when given"
            )


@dataclass(frozen=True, slots=True)
class EvidenceItem(ValueObject):
    """One piece of clinical evidence, tagged by `polarity` (supporting
    or contradicting the clinical picture) and carrying a `weight` — see
    `EvidencePolarity`'s own docstring for why "Supporting Evidence"/
    "Contradicting Evidence" are computed views over one collection of
    these, and `application/services/evidence_analysis_service
    .EvidenceAnalysisService.weight_evidence` for how `weight` is
    deterministically adjusted after generation."""

    description: str
    weight: float
    polarity: EvidencePolarity


@dataclass(frozen=True, slots=True)
class RedFlag(ValueObject):
    """One red-flag indicator, carrying a `priority` — see
    `RedFlagPriority`'s own docstring for how "risk scoring" drives
    escalation across this ordering."""

    description: str
    priority: RedFlagPriority


@dataclass(frozen=True, slots=True)
class MedicalReasoningResult(ValueObject):
    """The canonical, structured reasoning result — always populated
    regardless of `output_format` (a rendering-time concern, per
    `application/services/clinical_summary_service.ClinicalSummaryService
    .render`'s own docstring), the same "generation produces structure;
    rendering produces presentation" split
    `app.modules.differential_diagnosis_ai.domain.value_objects
    .DifferentialDiagnosisResult` establishes for itself.

    `supporting_evidence`/`contradicting_evidence` are computed
    properties over the single `evidence` collection, filtered by
    `EvidenceItem.polarity` — never separately stored, so the two views
    can never drift out of sync with each other."""

    clinical_summary: str
    evidence: tuple[EvidenceItem, ...]
    missing_information: tuple[str, ...]
    clinical_confidence: float | None
    diagnostic_confidence: float | None
    therapeutic_confidence: float | None
    risk_factors: tuple[str, ...]
    red_flags: tuple[RedFlag, ...]
    suggested_next_questions: tuple[str, ...]
    suggested_investigations: tuple[str, ...]
    suggested_monitoring: tuple[str, ...]
    clinical_justification: str
    raw_text: str
    output_format: MedicalReasoningOutputFormat

    @property
    def supporting_evidence(self) -> tuple[EvidenceItem, ...]:
        return tuple(item for item in self.evidence if item.polarity is EvidencePolarity.SUPPORTING)

    @property
    def contradicting_evidence(self) -> tuple[EvidenceItem, ...]:
        return tuple(
            item for item in self.evidence if item.polarity is EvidencePolarity.CONTRADICTING
        )

    @property
    def is_empty(self) -> bool:
        return (
            not self.clinical_summary.strip()
            and not self.evidence
            and not self.risk_factors
            and not self.red_flags
            and not self.suggested_next_questions
            and not self.suggested_investigations
            and not self.suggested_monitoring
            and not self.clinical_justification.strip()
        )


@dataclass(frozen=True, slots=True)
class MedicalReasoningTemplateSet(ValueObject):
    """The three AI-Foundation-registered prompt template names (system/
    developer/user) and pinned version
    `MedicalReasoningTemplateSelectorPort.select` resolves a
    `ReasoningSetting` to — see
    `infrastructure/prompts/template_selector.py`."""

    system_template_name: str
    developer_template_name: str
    user_template_name: str
    version: int


@dataclass(frozen=True, slots=True)
class GenerationSession(ValueObject):
    """The tracked record of one reasoning attempt, per this task's own
    "AUDIT — provider, model, latency, token usage, reasoning status"
    requirement. `provider`/`model` are plain `str`, not AI Foundation's
    own `AIProviderType`/`AIModel` — this module's domain does not import
    even AI Foundation's *public* types (see this module's own
    docstring)."""

    generation_id: UUID
    provider: str
    model: str
    reasoning_setting: str
    language: str
    status: ReasoningStatus
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class MedicalReasoningStreamChunk(ValueObject):
    """One increment of a streamed generation — see
    `infrastructure/generation/medical_reasoning_generator.py`'s own
    docstring for why this is a post-hoc chunking of one complete AI
    Foundation call rather than true token-level streaming."""

    delta: str
    is_final: bool = False
