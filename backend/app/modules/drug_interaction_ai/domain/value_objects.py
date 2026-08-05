"""Value objects for the AI Drug Interaction & Medication Safety
module's domain.

None of these reference another module's `domain`/`application`/
`infrastructure` type — every cross-module identity (organization,
patient) is a plain `UUID`, and clinical content is exactly what this
task's own SUPPORTED INPUT specification calls for: values the caller
supplies directly, the same "explicit encounter input only" design every
prior AI module's own value-objects module docstring establishes for
itself. Unlike every prior AI module, this task's own SUPPORTED INPUT
section names no visit context, clinical notes, or sibling-AI-module
context fields at all — only medication and patient-safety data — so
none of those fields are invented here; see `container.py`'s own scope
note for why that also means no live cross-module lookups are needed
beyond `MedicalReasoningAIPort.score_confidence`.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.modules.drug_interaction_ai.domain.enums import (
    DrugInteractionOutputFormat,
    DrugInteractionSetting,
    EvidenceLevel,
    LactationStatus,
    PregnancyStatus,
    SafetyAnalysisStatus,
    SafetyIssueCategory,
    SafetySeverity,
)
from app.modules.drug_interaction_ai.domain.exceptions import (
    DuplicateMedicationError,
    EmptyMedicationListError,
    InvalidDrugInteractionInputError,
)
from app.shared.domain.value_object import ValueObject

_MAX_PLAUSIBLE_AGE = 150


@dataclass(frozen=True, slots=True)
class MedicationEntry(ValueObject):
    """One medication — used for every entry in `current_medications`
    and for `new_prescription`. This task's own SUPPORTED INPUT section
    names "Drug name, Generic name, Brand name, Dose, Frequency, Route,
    Duration" as a flat list; read together, these are exactly the
    fields of a single medication entry, applied uniformly to both
    "Current medications" and "New prescription" rather than two
    bespoke, near-duplicate shapes."""

    drug_name: str
    generic_name: str | None = None
    brand_name: str | None = None
    dose: str | None = None
    frequency: str | None = None
    route: str | None = None
    duration: str | None = None

    def __post_init__(self) -> None:
        if not self.drug_name.strip():
            raise InvalidDrugInteractionInputError("drug_name must not be blank")


@dataclass(frozen=True, slots=True)
class DrugInteractionAnalysisInput(ValueObject):
    organization_id: UUID
    patient_id: UUID
    medication_setting: DrugInteractionSetting
    current_medications: tuple[MedicationEntry, ...] = ()
    new_prescription: MedicationEntry | None = None
    diagnosis: str | None = None
    problem_list: tuple[str, ...] = ()
    allergies: tuple[str, ...] = ()
    medical_conditions: tuple[str, ...] = ()
    pregnancy_status: PregnancyStatus | None = None
    lactation_status: LactationStatus | None = None
    patient_age: int | None = None
    patient_weight_kg: float | None = None
    renal_function: str | None = None
    hepatic_function: str | None = None
    recent_lab_values: tuple[str, ...] = ()
    language: str = "en"
    output_format: DrugInteractionOutputFormat = DrugInteractionOutputFormat.JSON

    def __post_init__(self) -> None:
        if not self.current_medications and self.new_prescription is None:
            raise EmptyMedicationListError()
        if not self.language.strip():
            raise InvalidDrugInteractionInputError("language must not be blank")
        if self.patient_age is not None and not (0 <= self.patient_age <= _MAX_PLAUSIBLE_AGE):
            raise InvalidDrugInteractionInputError(
                f"patient_age must be between 0 and {_MAX_PLAUSIBLE_AGE} when given"
            )
        if self.patient_weight_kg is not None and self.patient_weight_kg <= 0:
            raise InvalidDrugInteractionInputError("patient_weight_kg must be positive when given")
        self._check_duplicate_medications()

    def _check_duplicate_medications(self) -> None:
        seen: set[tuple[str, str | None, str | None, str | None]] = set()
        for medication in self.current_medications:
            key = (
                medication.drug_name.strip().lower(),
                medication.dose,
                medication.frequency,
                medication.route,
            )
            if key in seen:
                raise DuplicateMedicationError(medication.drug_name)
            seen.add(key)


@dataclass(frozen=True, slots=True)
class SafetyIssue(ValueObject):
    """One detected medication-safety concern — `category` tags which of
    this task's own eighteen DETECT concerns it represents, and
    `severity`/`mechanism`/`clinical_significance`/`evidence_level` are
    exactly this task's own "Interaction Severity"/"Mechanism"/"Clinical
    Significance"/"Evidence Level" OUTPUT sub-fields, applied uniformly
    to every category rather than only to drug-drug interactions —
    a duplicate-therapy or contraindication concern deserves the same
    structured severity/mechanism/evidence treatment a drug-drug
    interaction does."""

    category: SafetyIssueCategory
    description: str
    severity: SafetySeverity
    mechanism: str | None = None
    clinical_significance: str | None = None
    evidence_level: EvidenceLevel | None = None
    involved_medications: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DrugInteractionAnalysisResult(ValueObject):
    """The canonical, structured safety-analysis result — always
    populated regardless of `output_format` (a rendering-time concern),
    the same "generation produces structure; rendering produces
    presentation" split every prior AI module's own result value object
    establishes for itself."""

    safety_summary: str
    interactions: tuple[SafetyIssue, ...]
    contraindications: tuple[str, ...]
    warnings: tuple[str, ...]
    monitoring_recommendations: tuple[str, ...]
    dose_adjustment_suggestions: tuple[str, ...]
    alternative_medication_suggestions: tuple[str, ...]
    patient_counseling_points: tuple[str, ...]
    clinical_reasoning: str
    confidence_score: float | None
    raw_text: str
    output_format: DrugInteractionOutputFormat

    @property
    def is_empty(self) -> bool:
        return (
            not self.safety_summary.strip()
            and not self.interactions
            and not self.contraindications
            and not self.warnings
            and not self.monitoring_recommendations
            and not self.dose_adjustment_suggestions
            and not self.alternative_medication_suggestions
            and not self.patient_counseling_points
            and not self.clinical_reasoning.strip()
        )


@dataclass(frozen=True, slots=True)
class DrugInteractionTemplateSet(ValueObject):
    """The three AI-Foundation-registered prompt template names (system/
    developer/user) and pinned version
    `DrugInteractionTemplateSelectorPort.select` resolves a
    `DrugInteractionSetting` to."""

    system_template_name: str
    developer_template_name: str
    user_template_name: str
    version: int


@dataclass(frozen=True, slots=True)
class GenerationSession(ValueObject):
    """The tracked record of one safety-analysis attempt, per this
    task's own "AUDIT — provider, model, latency, token usage, safety
    analysis status" requirement. `medication_setting` is carried beyond
    the literal AUDIT list, the same "each session also carries its own
    setting/language" precedent every prior AI module's own
    `GenerationSession` establishes for itself."""

    generation_id: UUID
    provider: str
    model: str
    medication_setting: str
    language: str
    status: SafetyAnalysisStatus
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class DrugInteractionStreamChunk(ValueObject):
    """One increment of a streamed generation — a post-hoc chunking of
    one complete AI Foundation call, the same shape every prior AI
    module's own stream chunk value object establishes for itself."""

    delta: str
    is_final: bool = False
