"""Value objects for the AI Pathology Interpretation module's domain.

None of these reference another module's `domain`/`application`/
`infrastructure` type — every cross-module identity (organization,
patient, visit) is a plain `UUID`, and clinical content is exactly what
this task's own SUPPORTED INPUT specification calls for: values the
caller supplies directly, the same "explicit encounter input only"
design every prior AI module's own value-objects module docstring
establishes for itself. `laboratory_interpretation`,
`radiology_interpretation`, and `medical_reasoning_context` are plain
`str | None` fields — this module never calls into
`app.modules.lab_interpretation_ai`'s,
`app.modules.radiology_interpretation_ai`'s, or
`app.modules.medical_reasoning_ai`'s generation pipelines directly; the
caller supplies whatever already-generated summary text it wants
considered, the same "explicit input, not a live cross-module lookup"
design `app.modules.radiology_interpretation_ai.domain.value_objects
.RadiologyInterpretationInput`'s own `laboratory_interpretation`/
`medical_reasoning_context` fields establish for themselves (see
`container.py`'s own scope note for the one genuine cross-module *port*
dependency this module does have — `MedicalReasoningAIPort
.score_confidence` — which is a use-case-level concern, not a domain
one).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.modules.pathology_interpretation_ai.domain.enums import (
    PathologyExaminationType,
    PathologyFindingCategory,
    PathologyInterpretationStatus,
    PathologyOutputFormat,
    PathologySetting,
    PatientSex,
    PregnancyStatus,
)
from app.modules.pathology_interpretation_ai.domain.exceptions import (
    EmptyPathologyReportError,
    InvalidPathologyInterpretationInputError,
    MalformedPathologyReportError,
)
from app.shared.domain.value_object import ValueObject

_MAX_PLAUSIBLE_AGE = 150
_MIN_REPORT_LENGTH = 10


@dataclass(frozen=True, slots=True)
class PathologyInterpretationInput(ValueObject):
    organization_id: UUID
    patient_id: UUID
    report_text: str
    examination_type: PathologyExaminationType
    pathology_setting: PathologySetting
    language: str = "en"
    visit_id: UUID | None = None
    patient_age: int | None = None
    patient_sex: PatientSex | None = None
    pregnancy_status: PregnancyStatus | None = None
    visit_type: str | None = None
    clinical_notes: tuple[str, ...] = ()
    soap_notes: tuple[str, ...] = ()
    icd10_suggestions: tuple[str, ...] = ()
    differential_diagnoses: tuple[str, ...] = ()
    laboratory_interpretation: str | None = None
    radiology_interpretation: str | None = None
    medical_reasoning_context: str | None = None
    output_format: PathologyOutputFormat = PathologyOutputFormat.JSON

    def __post_init__(self) -> None:
        if not self.report_text.strip():
            raise EmptyPathologyReportError()
        stripped = self.report_text.strip()
        if len(stripped) < _MIN_REPORT_LENGTH or not any(char.isalpha() for char in stripped):
            raise MalformedPathologyReportError(
                f"report_text must be at least {_MIN_REPORT_LENGTH} characters and contain "
                "alphabetic content"
            )
        if not self.language.strip():
            raise InvalidPathologyInterpretationInputError("language must not be blank")
        if self.patient_age is not None and not (0 <= self.patient_age <= _MAX_PLAUSIBLE_AGE):
            raise InvalidPathologyInterpretationInputError(
                f"patient_age must be between 0 and {_MAX_PLAUSIBLE_AGE} when given"
            )


@dataclass(frozen=True, slots=True)
class PathologyFinding(ValueObject):
    """One interpreted microscopic finding — `category` is the AI's own
    classification, deterministically reconciled against a curated
    keyword table by `application/services
    /malignancy_assessment_service.MalignancyAssessmentService` (see
    `ClinicalCorrelationPort`'s own docstring)."""

    description: str
    category: PathologyFindingCategory
    anatomical_site: str | None = None


@dataclass(frozen=True, slots=True)
class PathologyInterpretationResult(ValueObject):
    """The canonical, structured interpretation result — always
    populated regardless of `output_format` (a rendering-time concern),
    the same "generation produces structure; rendering produces
    presentation" split every prior AI module's own result value object
    establishes for itself.

    `benign_features`/`malignant_features`/`atypical_findings` are
    computed properties over the single `microscopic_findings`
    collection, filtered by `PathologyFinding.category` — never
    separately stored, so these three views (this task's own "Benign
    Features"/"Malignant Features"/"Atypical Findings" OUTPUT fields) can
    never drift out of sync with `microscopic_findings` itself (this
    task's own "Microscopic Findings" OUTPUT field — the full,
    unfiltered collection). `key_findings` is a separate, directly
    AI-reported highlight list (this task's own "Key Findings" OUTPUT
    field) — not a filtered view of `microscopic_findings`, since the
    most clinically important points of a report are not always a strict
    subset of its microscopic description (they may draw on gross
    description or clinical correlation as well).
    """

    pathology_summary: str
    key_findings: tuple[str, ...]
    microscopic_findings: tuple[PathologyFinding, ...]
    final_impression: str
    clinical_significance: str
    correlation_recommendations: tuple[str, ...]
    suggested_follow_up: tuple[str, ...]
    suggested_specialist_referral: tuple[str, ...]
    red_flag_warnings: tuple[str, ...]
    confidence_score: float | None
    clinical_reasoning: str
    raw_text: str
    output_format: PathologyOutputFormat

    @property
    def benign_features(self) -> tuple[PathologyFinding, ...]:
        return tuple(
            f for f in self.microscopic_findings if f.category is PathologyFindingCategory.BENIGN
        )

    @property
    def malignant_features(self) -> tuple[PathologyFinding, ...]:
        return tuple(
            f for f in self.microscopic_findings if f.category is PathologyFindingCategory.MALIGNANT
        )

    @property
    def atypical_findings(self) -> tuple[PathologyFinding, ...]:
        return tuple(
            f for f in self.microscopic_findings if f.category is PathologyFindingCategory.ATYPICAL
        )

    @property
    def is_empty(self) -> bool:
        return (
            not self.pathology_summary.strip()
            and not self.key_findings
            and not self.microscopic_findings
            and not self.final_impression.strip()
            and not self.clinical_significance.strip()
            and not self.correlation_recommendations
            and not self.suggested_follow_up
            and not self.suggested_specialist_referral
            and not self.red_flag_warnings
            and not self.clinical_reasoning.strip()
        )


@dataclass(frozen=True, slots=True)
class PathologyInterpretationTemplateSet(ValueObject):
    """The three AI-Foundation-registered prompt template names (system/
    developer/user) and pinned version
    `PathologyInterpretationTemplateSelectorPort.select` resolves a
    `PathologySetting` to."""

    system_template_name: str
    developer_template_name: str
    user_template_name: str
    version: int


@dataclass(frozen=True, slots=True)
class GenerationSession(ValueObject):
    """The tracked record of one interpretation attempt, per this task's
    own "AUDIT — provider, model, latency, token usage, interpretation
    status" requirement. `pathology_setting`/`examination_type` are
    carried beyond the literal AUDIT list, the same "each session also
    carries its own setting/language" precedent every prior AI module's
    own `GenerationSession` establishes for itself."""

    generation_id: UUID
    provider: str
    model: str
    pathology_setting: str
    examination_type: str
    language: str
    status: PathologyInterpretationStatus
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class PathologyInterpretationStreamChunk(ValueObject):
    """One increment of a streamed generation — a post-hoc chunking of
    one complete AI Foundation call, the same shape every prior AI
    module's own stream chunk value object establishes for itself."""

    delta: str
    is_final: bool = False
