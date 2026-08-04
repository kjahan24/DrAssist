"""Enums owned by the AI Lab Interpretation module's domain."""

from enum import StrEnum


class LabInterpretationSetting(StrEnum):
    """Drives prompt selection (`infrastructure/prompts/
    template_selector.py`) — each setting has its own independently-
    versioned prompt template set. Same five-member vocabulary, in the
    same order, as this task's own PROMPTS section, and a same-*shaped*
    (not shared) local copy of
    `app.modules.medical_reasoning_ai.domain.enums.ReasoningSetting` —
    domain code never imports a peer module's domain enum."""

    OUTPATIENT = "outpatient"
    INPATIENT = "inpatient"
    EMERGENCY = "emergency"
    PEDIATRIC = "pediatric"
    GERIATRIC = "geriatric"


class LabInterpretationOutputFormat(StrEnum):
    """What shape a result is rendered into."""

    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"


class LabFindingFlag(StrEnum):
    """The closed vocabulary a single `LabFinding` is tagged with.
    `LabInterpretationResult.abnormal_findings`/`.critical_values` are
    computed views over one unified `findings` collection filtered by
    this tag — see that value object's own docstring — rather than two
    separately-tracked collections that could drift out of sync."""

    NORMAL = "normal"
    ABNORMAL_LOW = "abnormal_low"
    ABNORMAL_HIGH = "abnormal_high"
    CRITICAL_LOW = "critical_low"
    CRITICAL_HIGH = "critical_high"


class LabInterpretationStatus(StrEnum):
    """Recorded on `GenerationSession` for this task's own AUDIT
    "interpretation status" field — named to match that wording exactly,
    the same reasoning
    `app.modules.medical_reasoning_ai.domain.enums.ReasoningStatus`
    documents for its own module's "reasoning status" wording."""

    COMPLETED = "completed"
    FAILED = "failed"


class PatientSex(StrEnum):
    """A same-shaped local copy of
    `app.modules.medical_reasoning_ai.domain.enums.PatientSex`."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNSPECIFIED = "unspecified"


class PregnancyStatus(StrEnum):
    """A same-shaped local copy of
    `app.modules.medical_reasoning_ai.domain.enums.PregnancyStatus` —
    pregnancy status is part of "Patient demographics" this task's own
    INPUT section asks for."""

    NOT_PREGNANT = "not_pregnant"
    PREGNANT = "pregnant"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
