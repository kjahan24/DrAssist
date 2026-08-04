"""Enums owned by the AI Medical Reasoning Engine's domain."""

from enum import StrEnum


class ReasoningSetting(StrEnum):
    """Drives prompt selection (`infrastructure/prompts/
    template_selector.py`) — each setting has its own independently-
    versioned prompt template set, the same "Support outpatient/
    inpatient/..." shape
    `app.modules.differential_diagnosis_ai.domain.enums.ClinicalSetting`
    establishes for its own module (a distinct member set, not shared —
    this task's own PROMPTS section lists its own five settings in its
    own order)."""

    OUTPATIENT = "outpatient"
    INPATIENT = "inpatient"
    EMERGENCY = "emergency"
    PEDIATRIC = "pediatric"
    GERIATRIC = "geriatric"


class MedicalReasoningOutputFormat(StrEnum):
    """What shape a result is rendered into. A same-shaped local copy of
    `app.modules.differential_diagnosis_ai.domain.enums
    .DifferentialOutputFormat` — domain code never imports across module
    boundaries (see `domain/value_objects.py`'s own module docstring)."""

    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"


class EvidencePolarity(StrEnum):
    """Whether one piece of evidence supports or contradicts the
    clinical picture being reasoned about. `MedicalReasoningResult`'s
    "Supporting Evidence"/"Contradicting Evidence" output fields are
    computed views over one unified `evidence` collection filtered by
    this tag, rather than two separately-tracked collections — see that
    value object's own docstring."""

    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"


class RedFlagPriority(StrEnum):
    """The closed vocabulary this task's own "red flag prioritization"
    reasoning-engine requirement needs to be meaningful — ordered from
    least to most acute, the same "small, closed vocabulary earns its own
    enum" reasoning `app.modules.differential_diagnosis_ai.domain.enums
    .UrgencyLevel` already establishes elsewhere in this codebase's AI
    modules. See `infrastructure/reasoning/default_evidence_analyzer.py`
    for how "risk scoring" drives escalation across this ordering."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class ReasoningStatus(StrEnum):
    """Recorded on `GenerationSession` for the "reasoning status" audit
    field this task asks for — named `ReasoningStatus`, not the
    `GenerationStatus` name every prior AI module uses, to match this
    task's own AUDIT wording exactly."""

    COMPLETED = "completed"
    FAILED = "failed"


class PatientSex(StrEnum):
    """A closed, small vocabulary (unlike free-text `language`), worth an
    enum the same way `app.modules.differential_diagnosis_ai.domain.enums
    .PatientSex` is for its own module — a same-*shaped*, not shared,
    local copy, since domain code never imports a peer module's domain
    enum."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNSPECIFIED = "unspecified"


class PregnancyStatus(StrEnum):
    """A same-shaped local copy of `app.modules.differential_diagnosis_ai
    .domain.enums.PregnancyStatus` — pregnancy status is part of "Patient
    demographics" this task's own INPUT section asks for."""

    NOT_PREGNANT = "not_pregnant"
    PREGNANT = "pregnant"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
