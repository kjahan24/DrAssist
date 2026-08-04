"""Value objects for the AI Lab Interpretation module's domain.

None of these reference another module's `domain`/`application`/
`infrastructure` type — every cross-module identity (organization,
patient, visit) is a plain `UUID`, and clinical content is exactly what
this task's own INPUT specification calls for: values the caller
supplies directly, the same "explicit encounter input only" design
`app.modules.medical_reasoning_ai.domain.value_objects`'s own module
docstring establishes for itself (that reasoning applies identically
here — see `container.py`'s own scope note for how this module still
achieves genuine reuse of `app.modules.medical_reasoning_ai` without
importing its *domain*, only its *public* port).

`LabValue` is this module's own generic representation of a single
laboratory result — deliberately **one** shape shared by every panel
this task's INPUT section names (CBC, CMP, BMP, Liver Function, Renal
Function, Lipid Profile, HbA1c, Blood Glucose, Thyroid Panel,
Coagulation Tests, Urinalysis, Electrolytes, CRP, ESR, Ferritin, Vitamin
Levels, Custom laboratory values) rather than one bespoke, near-duplicate
structure per panel: every one of those panels is, at the individual-
result level, the same (test name, reported value, optional numeric
value, optional unit, optional reference range) shape. "Custom
laboratory values" being explicitly listed alongside seventeen named
panels is itself evidence that a fixed schema-per-panel design was not
intended.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import isfinite
from uuid import UUID

from app.modules.lab_interpretation_ai.domain.enums import (
    LabFindingFlag,
    LabInterpretationOutputFormat,
    LabInterpretationSetting,
    LabInterpretationStatus,
    PatientSex,
    PregnancyStatus,
)
from app.modules.lab_interpretation_ai.domain.exceptions import (
    DuplicateLabValueError,
    ImpossibleLabValueRangeError,
    InvalidLabInterpretationInputError,
    InvalidLabUnitError,
    MalformedLabValueError,
)
from app.shared.domain.value_object import ValueObject

_MAX_PLAUSIBLE_AGE = 150


@dataclass(frozen=True, slots=True)
class LabValue(ValueObject):
    """One caller-supplied laboratory result. `value` is the as-reported
    text (covers qualitative results like a urinalysis "trace"/"positive"
    reading, not just numeric ones); `numeric_value` is the parsed
    numeric form when the result is quantitative, `None` otherwise.
    `panel` is an optional caller-supplied categorization (e.g. "CBC",
    "CMP") — purely informative, never required, since this value
    object's own shape already covers every panel uniformly.

    `__post_init__` performs this task's own "malformed lab data"/
    "impossible numeric ranges"/"invalid units" Tier-3 checks — see
    `domain/exceptions.py`'s own module docstring for the exact mapping.
    Deliberately generic rather than per-test-name reference-range
    checks (that deeper, knowledge-dependent classification is
    `CriticalValueAnalyzerPort`'s own job, applied to the AI's *output*
    findings, not caller input): a negative or non-finite numeric result
    is impossible for **any** laboratory test, and a whitespace-only unit
    string is malformed for **any** test, so both checks are safe,
    universal, and do not risk rejecting a legitimate but uncommon test
    a fixed per-test table would not recognize.
    """

    test_name: str
    value: str
    numeric_value: float | None = None
    unit: str | None = None
    reference_range: str | None = None
    panel: str | None = None
    collected_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.test_name.strip():
            raise MalformedLabValueError("test_name must not be blank")
        if not self.value.strip():
            raise MalformedLabValueError(f"{self.test_name!r} is missing a reported value")
        if self.numeric_value is not None and (
            not isfinite(self.numeric_value) or self.numeric_value < 0
        ):
            raise ImpossibleLabValueRangeError(self.test_name)
        if self.unit is not None and not self.unit.strip():
            raise InvalidLabUnitError(self.test_name)


@dataclass(frozen=True, slots=True)
class LabInterpretationInput(ValueObject):
    organization_id: UUID
    patient_id: UUID
    lab_values: tuple[LabValue, ...]
    lab_setting: LabInterpretationSetting
    language: str = "en"
    visit_id: UUID | None = None
    patient_age: int | None = None
    patient_sex: PatientSex | None = None
    pregnancy_status: PregnancyStatus | None = None
    medical_conditions: tuple[str, ...] = ()
    allergies: tuple[str, ...] = ()
    medications: tuple[str, ...] = ()
    visit_type: str | None = None
    clinical_notes: tuple[str, ...] = ()
    soap_notes: tuple[str, ...] = ()
    output_format: LabInterpretationOutputFormat = LabInterpretationOutputFormat.JSON

    def __post_init__(self) -> None:
        if not self.lab_values:
            raise InvalidLabInterpretationInputError("lab_values must not be empty")
        if not self.language.strip():
            raise InvalidLabInterpretationInputError("language must not be blank")
        if self.patient_age is not None and not (0 <= self.patient_age <= _MAX_PLAUSIBLE_AGE):
            raise InvalidLabInterpretationInputError(
                f"patient_age must be between 0 and {_MAX_PLAUSIBLE_AGE} when given"
            )
        self._check_duplicate_lab_values()

    def _check_duplicate_lab_values(self) -> None:
        seen: set[tuple[str, str, datetime | None]] = set()
        for lab_value in self.lab_values:
            key = (
                lab_value.test_name.strip().lower(),
                lab_value.value.strip().lower(),
                lab_value.collected_at,
            )
            if key in seen:
                raise DuplicateLabValueError(lab_value.test_name)
            seen.add(key)


@dataclass(frozen=True, slots=True)
class LabFinding(ValueObject):
    """One interpreted laboratory finding — `flag` is the AI's own
    classification, deterministically reconciled against a curated
    reference table by `application/services
    /critical_value_detection_service.CriticalValueDetectionService
    .reconcile_findings` (see `CriticalValueAnalyzerPort`'s own
    docstring)."""

    test_name: str
    value: str
    numeric_value: float | None
    unit: str | None
    flag: LabFindingFlag


@dataclass(frozen=True, slots=True)
class LabInterpretationResult(ValueObject):
    """The canonical, structured interpretation result — always
    populated regardless of `output_format` (a rendering-time concern),
    the same "generation produces structure; rendering produces
    presentation" split every prior AI module's own result value object
    establishes for itself.

    `abnormal_findings`/`critical_values` are computed properties over
    the single `findings` collection, filtered by `LabFinding.flag` —
    never separately stored, so the two views (this task's own "Abnormal
    Findings"/"Critical Values" OUTPUT fields) can never drift out of
    sync with each other.
    """

    overall_interpretation: str
    findings: tuple[LabFinding, ...]
    clinical_significance: str
    supporting_evidence: tuple[str, ...]
    potential_causes: tuple[str, ...]
    suggested_follow_up_tests: tuple[str, ...]
    monitoring_recommendations: tuple[str, ...]
    red_flag_warnings: tuple[str, ...]
    confidence_score: float | None
    raw_text: str
    output_format: LabInterpretationOutputFormat

    @property
    def abnormal_findings(self) -> tuple[LabFinding, ...]:
        abnormal_flags = (LabFindingFlag.ABNORMAL_LOW, LabFindingFlag.ABNORMAL_HIGH)
        return tuple(f for f in self.findings if f.flag in abnormal_flags)

    @property
    def critical_values(self) -> tuple[LabFinding, ...]:
        critical_flags = (LabFindingFlag.CRITICAL_LOW, LabFindingFlag.CRITICAL_HIGH)
        return tuple(f for f in self.findings if f.flag in critical_flags)

    @property
    def is_empty(self) -> bool:
        return (
            not self.overall_interpretation.strip()
            and not self.findings
            and not self.clinical_significance.strip()
            and not self.supporting_evidence
            and not self.potential_causes
            and not self.suggested_follow_up_tests
            and not self.monitoring_recommendations
            and not self.red_flag_warnings
        )


@dataclass(frozen=True, slots=True)
class LabInterpretationTemplateSet(ValueObject):
    """The three AI-Foundation-registered prompt template names (system/
    developer/user) and pinned version
    `LabInterpretationTemplateSelectorPort.select` resolves a
    `LabInterpretationSetting` to."""

    system_template_name: str
    developer_template_name: str
    user_template_name: str
    version: int


@dataclass(frozen=True, slots=True)
class GenerationSession(ValueObject):
    """The tracked record of one interpretation attempt, per this task's
    own "AUDIT — provider, model, latency, token usage, interpretation
    status" requirement."""

    generation_id: UUID
    provider: str
    model: str
    lab_setting: str
    language: str
    status: LabInterpretationStatus
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class LabInterpretationStreamChunk(ValueObject):
    """One increment of a streamed generation — a post-hoc chunking of
    one complete AI Foundation call, the same shape every prior AI
    module's own stream chunk value object establishes for itself."""

    delta: str
    is_final: bool = False
