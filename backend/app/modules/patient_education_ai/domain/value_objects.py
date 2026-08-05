"""Value objects for the AI Patient Education & Discharge Instructions
module's domain.

None of these reference another module's `domain`/`application`/
`infrastructure` type — every cross-module identity (organization,
patient) is a plain `UUID`, and clinical content is exactly what this
task's own SUPPORTED INPUT specification calls for: values the caller
supplies directly, the same "explicit encounter input only" design every
prior AI module's own value-objects module docstring establishes for
itself. `prescription_ai_output`, `drug_interaction_ai_output`,
`risk_stratification_ai_output`, `laboratory_interpretation`,
`radiology_interpretation`, `pathology_interpretation`,
`medical_reasoning_context`, and `differential_diagnosis_context` are
all plain `str | None` fields — this module never calls into any of
those seven peer modules' own generation pipelines directly; the caller
supplies whatever already-generated summary text it wants considered,
the same "explicit input, not a live cross-module lookup" design
`app.modules.risk_stratification_ai.domain.value_objects
.RiskStratificationInput`'s own equivalent fields establish for
themselves (see `container.py`'s own scope note for the one genuine
cross-module *port* dependency this module does have —
`MedicalReasoningAIPort.score_confidence` — which is a use-case-level
concern, not a domain one).

Unlike every prior AI module, this domain layer defines no per-item
value object (no `RiskScore`, no `SafetyIssue`) — this task's own
GENERATE/OUTPUT sections describe flat, free-text educational content
(a diagnosis explanation, a list of medication instructions, a list of
warning signs), never a structured per-item shape with its own
sub-fields, so `PatientEducationResult`'s own fields are plain
`str`/`tuple[str, ...]`, matching that flatter shape exactly rather than
inventing unrequested structure.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

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
from app.shared.domain.value_object import ValueObject

_MAX_PLAUSIBLE_AGE = 150


@dataclass(frozen=True, slots=True)
class PatientEducationInput(ValueObject):
    organization_id: UUID
    patient_id: UUID
    education_setting: PatientEducationSetting
    diagnoses: tuple[str, ...]
    current_medications: tuple[str, ...]
    patient_age: int | None = None
    clinical_notes: tuple[str, ...] = ()
    soap_notes: tuple[str, ...] = ()
    prescription_ai_output: str | None = None
    drug_interaction_ai_output: str | None = None
    risk_stratification_ai_output: str | None = None
    laboratory_interpretation: str | None = None
    radiology_interpretation: str | None = None
    pathology_interpretation: str | None = None
    medical_reasoning_context: str | None = None
    differential_diagnosis_context: str | None = None
    language: str = "en"
    output_format: PatientEducationOutputFormat = PatientEducationOutputFormat.JSON

    def __post_init__(self) -> None:
        if not self.diagnoses:
            raise MissingDiagnosisError()
        if not self.current_medications:
            raise MissingMedicationListError()
        if not self.language.strip():
            raise InvalidPatientEducationInputError("language must not be blank")
        if self.patient_age is not None and not (0 <= self.patient_age <= _MAX_PLAUSIBLE_AGE):
            raise InvalidPatientEducationInputError(
                f"patient_age must be between 0 and {_MAX_PLAUSIBLE_AGE} when given"
            )


@dataclass(frozen=True, slots=True)
class PatientEducationResult(ValueObject):
    """The canonical, structured patient education result — always
    populated regardless of `output_format` (a rendering-time concern),
    the same "generation produces structure; rendering produces
    presentation" split every prior AI module's own result value object
    establishes for itself.

    Deliberately carries no `clinical_reasoning` field — unlike every
    prior AI module, this task's own twelve-item OUTPUT list does not
    name one, so none is added, the same "stay disciplined about not
    inventing unrequested structure" precedent
    `app.modules.risk_stratification_ai.domain.value_objects
    .RiskScore`'s own docstring documents for its own omitted field.
    """

    patient_summary: str
    diagnosis_explanation: str
    medication_instructions: tuple[str, ...]
    home_care_plan: tuple[str, ...]
    lifestyle_advice: tuple[str, ...]
    diet_advice: tuple[str, ...]
    exercise_advice: tuple[str, ...]
    warning_signs: tuple[str, ...]
    emergency_instructions: tuple[str, ...]
    follow_up_plan: tuple[str, ...]
    patient_checklist: tuple[str, ...]
    confidence_score: float | None
    raw_text: str
    output_format: PatientEducationOutputFormat

    @property
    def is_empty(self) -> bool:
        return (
            not self.patient_summary.strip()
            and not self.diagnosis_explanation.strip()
            and not self.medication_instructions
            and not self.home_care_plan
            and not self.lifestyle_advice
            and not self.diet_advice
            and not self.exercise_advice
            and not self.warning_signs
            and not self.emergency_instructions
            and not self.follow_up_plan
            and not self.patient_checklist
        )


@dataclass(frozen=True, slots=True)
class PatientEducationTemplateSet(ValueObject):
    """The three AI-Foundation-registered prompt template names (system/
    developer/user) and pinned version
    `PatientEducationAnalysisTemplateSelectorPort.select` resolves a
    `PatientEducationSetting` to."""

    system_template_name: str
    developer_template_name: str
    user_template_name: str
    version: int


@dataclass(frozen=True, slots=True)
class GenerationSession(ValueObject):
    """The tracked record of one education-generation attempt, per this
    task's own "AUDIT — provider, model, latency, token usage, education
    generation status" requirement. `education_setting` is carried
    beyond the literal AUDIT list, the same "each session also carries
    its own setting/language" precedent every prior AI module's own
    `GenerationSession` establishes for itself."""

    generation_id: UUID
    provider: str
    model: str
    education_setting: str
    language: str
    status: EducationGenerationStatus
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class PatientEducationStreamChunk(ValueObject):
    """One increment of a streamed generation — a post-hoc chunking of
    one complete AI Foundation call, the same shape every prior AI
    module's own stream chunk value object establishes for itself."""

    delta: str
    is_final: bool = False
