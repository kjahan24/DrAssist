"""Value objects for the AI Radiology Interpretation module's domain.

None of these reference another module's `domain`/`application`/
`infrastructure` type — every cross-module identity (organization,
patient, visit) is a plain `UUID`, and clinical content is exactly what
this task's own SUPPORTED INPUT specification calls for: values the
caller supplies directly, the same "explicit encounter input only"
design every prior AI module's own value-objects module docstring
establishes for itself. `laboratory_interpretation` and
`medical_reasoning_context` are plain `str | None` fields — this
module never calls into `app.modules.lab_interpretation_ai`'s or
`app.modules.medical_reasoning_ai`'s generation pipelines directly; the
caller supplies whatever already-generated summary text it wants
considered, the same "explicit input, not a live cross-module lookup"
design `app.modules.medical_reasoning_ai.domain.value_objects
.MedicalReasoningInput`'s own `icd10_suggestions`/`differential_diagnoses`
fields establish for themselves (see `container.py`'s own scope note for
the one genuine cross-module *port* dependency this module does have —
`MedicalReasoningAIPort.score_confidence` — which is a use-case-level
concern, not a domain one).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.modules.radiology_interpretation_ai.domain.enums import (
    PatientSex,
    PregnancyStatus,
    RadiologyExaminationType,
    RadiologyFindingCategory,
    RadiologyInterpretationStatus,
    RadiologyOutputFormat,
    RadiologySetting,
)
from app.modules.radiology_interpretation_ai.domain.exceptions import (
    EmptyRadiologyReportError,
    InvalidRadiologyInterpretationInputError,
    MalformedRadiologyReportError,
)
from app.shared.domain.value_object import ValueObject

_MAX_PLAUSIBLE_AGE = 150
_MIN_REPORT_LENGTH = 10


@dataclass(frozen=True, slots=True)
class RadiologyInterpretationInput(ValueObject):
    organization_id: UUID
    patient_id: UUID
    report_text: str
    examination_type: RadiologyExaminationType
    radiology_setting: RadiologySetting
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
    medical_reasoning_context: str | None = None
    output_format: RadiologyOutputFormat = RadiologyOutputFormat.JSON

    def __post_init__(self) -> None:
        if not self.report_text.strip():
            raise EmptyRadiologyReportError()
        stripped = self.report_text.strip()
        if len(stripped) < _MIN_REPORT_LENGTH or not any(char.isalpha() for char in stripped):
            raise MalformedRadiologyReportError(
                f"report_text must be at least {_MIN_REPORT_LENGTH} characters and contain "
                "alphabetic content"
            )
        if not self.language.strip():
            raise InvalidRadiologyInterpretationInputError("language must not be blank")
        if self.patient_age is not None and not (0 <= self.patient_age <= _MAX_PLAUSIBLE_AGE):
            raise InvalidRadiologyInterpretationInputError(
                f"patient_age must be between 0 and {_MAX_PLAUSIBLE_AGE} when given"
            )


@dataclass(frozen=True, slots=True)
class RadiologyFinding(ValueObject):
    """One interpreted radiology finding — `category` is the AI's own
    classification, deterministically reconciled against a curated
    keyword table by `application/services
    /critical_finding_detection_service.CriticalFindingDetectionService`
    (see `FindingExtractionPort`'s own docstring)."""

    description: str
    category: RadiologyFindingCategory
    anatomical_region: str | None = None


@dataclass(frozen=True, slots=True)
class RadiologyInterpretationResult(ValueObject):
    """The canonical, structured interpretation result — always
    populated regardless of `output_format` (a rendering-time concern),
    the same "generation produces structure; rendering produces
    presentation" split every prior AI module's own result value object
    establishes for itself.

    `normal_findings`/`abnormal_findings`/`incidental_findings`/
    `critical_findings`/`important_findings` are computed properties over
    the single `findings` collection, filtered by `RadiologyFinding
    .category` — never separately stored, so these five views (this
    task's own "Normal Findings"/"Abnormal Findings"/"Incidental
    Findings"/"Critical Findings"/"Important Findings" OUTPUT fields) can
    never drift out of sync with each other. `important_findings` is
    every finding that is not `NORMAL` — the direct reading of
    "important" as "clinically noteworthy," i.e. everything a normal-limits
    finding is explicitly not.
    """

    examination_summary: str
    findings: tuple[RadiologyFinding, ...]
    clinical_significance: str
    differential_imaging_considerations: tuple[str, ...]
    suggested_follow_up_imaging: tuple[str, ...]
    suggested_specialist_referral: tuple[str, ...]
    red_flag_warnings: tuple[str, ...]
    confidence_score: float | None
    clinical_reasoning: str
    raw_text: str
    output_format: RadiologyOutputFormat

    @property
    def normal_findings(self) -> tuple[RadiologyFinding, ...]:
        return tuple(f for f in self.findings if f.category is RadiologyFindingCategory.NORMAL)

    @property
    def abnormal_findings(self) -> tuple[RadiologyFinding, ...]:
        return tuple(f for f in self.findings if f.category is RadiologyFindingCategory.ABNORMAL)

    @property
    def incidental_findings(self) -> tuple[RadiologyFinding, ...]:
        return tuple(f for f in self.findings if f.category is RadiologyFindingCategory.INCIDENTAL)

    @property
    def critical_findings(self) -> tuple[RadiologyFinding, ...]:
        return tuple(f for f in self.findings if f.category is RadiologyFindingCategory.CRITICAL)

    @property
    def important_findings(self) -> tuple[RadiologyFinding, ...]:
        return tuple(f for f in self.findings if f.category is not RadiologyFindingCategory.NORMAL)

    @property
    def is_empty(self) -> bool:
        return (
            not self.examination_summary.strip()
            and not self.findings
            and not self.clinical_significance.strip()
            and not self.differential_imaging_considerations
            and not self.suggested_follow_up_imaging
            and not self.suggested_specialist_referral
            and not self.red_flag_warnings
            and not self.clinical_reasoning.strip()
        )


@dataclass(frozen=True, slots=True)
class RadiologyInterpretationTemplateSet(ValueObject):
    """The three AI-Foundation-registered prompt template names (system/
    developer/user) and pinned version
    `RadiologyInterpretationTemplateSelectorPort.select` resolves a
    `RadiologySetting` to."""

    system_template_name: str
    developer_template_name: str
    user_template_name: str
    version: int


@dataclass(frozen=True, slots=True)
class GenerationSession(ValueObject):
    """The tracked record of one interpretation attempt, per this task's
    own "AUDIT — provider, model, latency, token usage, interpretation
    status" requirement. `radiology_setting`/`examination_type` are
    carried beyond the literal AUDIT list, the same "each session also
    carries its own setting/language" precedent every prior AI module's
    own `GenerationSession` establishes for itself."""

    generation_id: UUID
    provider: str
    model: str
    radiology_setting: str
    examination_type: str
    language: str
    status: RadiologyInterpretationStatus
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class RadiologyInterpretationStreamChunk(ValueObject):
    """One increment of a streamed generation — a post-hoc chunking of
    one complete AI Foundation call, the same shape every prior AI
    module's own stream chunk value object establishes for itself."""

    delta: str
    is_final: bool = False
