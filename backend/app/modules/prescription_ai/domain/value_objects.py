"""Value objects for the AI Prescription Assistance module's domain.

None of these reference another module's `domain`/`application`/
`infrastructure` type — every cross-module identity (organization,
patient, visit) is a plain `UUID`, and clinical content (chief complaint,
HPI, symptoms, ROS, physical exam, vitals, assessment, plan, clinical/
SOAP note text, ICD-10 suggestions, existing medications, allergies,
medical conditions, laboratory results) is exactly what the task's own
INPUT specification calls for: values the caller supplies directly, not
records looked up from the Clinical Note AI/SOAP Note AI/ICD-10 AI/
Prescriptions modules. This module never queries another module's public
port — its entire input is self-contained clinical context, the same
design `app.modules.icd10_ai.domain.value_objects` establishes for itself
(see that module's own module docstring for the full reasoning, which
applies identically here). In particular, `icd10_suggestions` is a tuple
of plain strings (code/description text) supplied by the caller — a
caller that already ran `app.modules.icd10_ai`'s own
`generate_suggestions` passes its result through as text here, the same
way `soap_note`/`clinical_note` are passed through as rendered text
rather than as those modules' own structured types.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.modules.prescription_ai.domain.enums import (
    AdministrationRoute,
    GenerationStatus,
    PatientSex,
    PregnancyStatus,
    PrescribingSetting,
    PrescriptionOutputFormat,
    SafetyFindingCategory,
    SafetySeverity,
)
from app.modules.prescription_ai.domain.exceptions import InvalidPrescriptionContextError
from app.shared.domain.value_object import ValueObject

_MAX_PLAUSIBLE_AGE = 150
_MAX_PLAUSIBLE_WEIGHT_KG = 500.0


@dataclass(frozen=True, slots=True)
class PrescriptionContextInput(ValueObject):
    organization_id: UUID
    patient_id: UUID
    chief_complaint: str
    prescribing_setting: PrescribingSetting
    language: str = "en"
    visit_id: UUID | None = None
    history_of_present_illness: str | None = None
    symptoms: tuple[str, ...] = ()
    review_of_systems: str | None = None
    physical_examination: str | None = None
    vitals: Mapping[str, str] = field(default_factory=dict)
    assessment: str | None = None
    plan: str | None = None
    clinical_note: str | None = None
    soap_note: str | None = None
    icd10_suggestions: tuple[str, ...] = ()
    existing_medications: tuple[str, ...] = ()
    allergies: tuple[str, ...] = ()
    medical_conditions: tuple[str, ...] = ()
    laboratory_results: tuple[str, ...] = ()
    patient_age: int | None = None
    patient_sex: PatientSex | None = None
    pregnancy_status: PregnancyStatus | None = None
    weight_kg: float | None = None
    visit_type: str | None = None
    output_format: PrescriptionOutputFormat = PrescriptionOutputFormat.JSON

    def __post_init__(self) -> None:
        if not self.chief_complaint.strip():
            raise InvalidPrescriptionContextError("chief_complaint must not be blank")
        if not self.language.strip():
            raise InvalidPrescriptionContextError("language must not be blank")
        if self.patient_age is not None and not (0 <= self.patient_age <= _MAX_PLAUSIBLE_AGE):
            raise InvalidPrescriptionContextError(
                f"patient_age must be between 0 and {_MAX_PLAUSIBLE_AGE} when given"
            )
        if self.weight_kg is not None and not (0 < self.weight_kg <= _MAX_PLAUSIBLE_WEIGHT_KG):
            raise InvalidPrescriptionContextError(
                f"weight_kg must be between 0 and {_MAX_PLAUSIBLE_WEIGHT_KG} when given"
            )


@dataclass(frozen=True, slots=True)
class MedicationSuggestion(ValueObject):
    """One draft medication suggestion, per this task's own OUTPUT
    specification. Every field this task lists is represented; `brand_name`
    and `confidence_score` are the two this task itself marks nullable
    ("Brand Name (optional)") or that this parser leaves nullable for the
    same "missing becomes a placeholder value, not a parse failure" split
    `app.modules.icd10_ai.domain.value_objects.ICD10Suggestion` documents
    for its own `confidence_score`. This module never validates
    `confidence_score` as a hard requirement — this task's own VALIDATION
    section does not list a "missing confidence score" category for this
    module (unlike AI ICD-10 Coding's)."""

    generic_name: str
    brand_name: str | None
    strength: str
    dosage: str
    route: AdministrationRoute
    frequency: str
    duration: str
    quantity: str
    is_prn: bool
    clinical_indication: str
    monitoring_advice: str
    patient_instructions: str
    confidence_score: float | None
    clinical_reasoning: str


@dataclass(frozen=True, slots=True)
class MedicationSafetyFinding(ValueObject):
    """One medication-safety concern, per this task's own "Drug
    Interaction Warnings, Allergy Warnings, Contraindications, Duplicate
    Therapy Detection" output requirement and "MEDICATION SAFETY"
    section's nine categories — unified into one shape tagged by
    `category` rather than nine separate value objects, since every
    category shares the same (category, severity, description, affected
    medications) structure.

    Populated from two independent sources, merged by
    `GeneratePrescriptionSuggestionUseCase`: findings the AI itself
    reports in its structured JSON response (semantic/contextual
    reasoning — pregnancy/pediatric/geriatric/renal/hepatic precautions
    are fundamentally clinical-judgment calls only the model can make),
    and findings computed deterministically via `DrugInteractionPort`/
    `MedicationKnowledgePort` against a curated reference table (a hard
    safety net for drug interactions, allergy cross-reactions, and
    duplicate therapeutic classes — the categories that *can* be checked
    without clinical judgment). See
    `application/services/medication_safety_analysis_service.py` for the
    deterministic half.
    """

    category: SafetyFindingCategory
    severity: SafetySeverity
    description: str
    affected_medications: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PrescriptionSuggestionSet(ValueObject):
    """The canonical, structured generation result — always populated
    regardless of `output_format` (a rendering-time concern, per
    `application/services/prescription_suggestion_renderer.py`'s own
    docstring), the same "generation produces structure; rendering
    produces presentation" split
    `app.modules.icd10_ai.domain.value_objects.ICD10SuggestionSet`
    establishes for itself."""

    medications: tuple[MedicationSuggestion, ...]
    safety_findings: tuple[MedicationSafetyFinding, ...]
    monitoring_recommendations: tuple[str, ...]
    follow_up_recommendations: tuple[str, ...]
    raw_text: str
    output_format: PrescriptionOutputFormat

    @property
    def is_empty(self) -> bool:
        return len(self.medications) == 0


@dataclass(frozen=True, slots=True)
class PrescriptionTemplateSet(ValueObject):
    """The three AI-Foundation-registered prompt template names (system/
    developer/user) and pinned version
    `PrescriptionTemplateSelectorPort.select` resolves a
    `PrescribingSetting` to — see
    `infrastructure/prompts/template_selector.py`."""

    system_template_name: str
    developer_template_name: str
    user_template_name: str
    version: int


@dataclass(frozen=True, slots=True)
class GenerationSession(ValueObject):
    """The tracked record of one generation attempt, per this task's own
    "AUDIT — Record provider, model, latency, token usage, generation
    status" requirement. `provider`/`model` are plain `str`, not AI
    Foundation's own `AIProviderType`/`AIModel` — this module's domain
    does not import even AI Foundation's *public* types (see this
    module's own docstring)."""

    generation_id: UUID
    provider: str
    model: str
    prescribing_setting: str
    language: str
    status: GenerationStatus
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class PrescriptionStreamChunk(ValueObject):
    """One increment of a streamed generation — see
    `infrastructure/generation/prescription_generator.py`'s own docstring
    for why this is a post-hoc chunking of one complete AI Foundation
    call rather than true token-level streaming."""

    delta: str
    is_final: bool = False
