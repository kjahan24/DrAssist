"""Enums owned by the AI Pathology Interpretation module's domain."""

from enum import StrEnum


class PathologyExaminationType(StrEnum):
    """The closed vocabulary of textual-report specimen/study types this
    task's own SUPPORTED INPUT section names, in the same order. This
    module never interprets microscope images or whole-slide images — it
    interprets the *textual report* of one of these examinations only,
    per this task's own GOAL section."""

    HISTOPATHOLOGY = "histopathology"
    CYTOPATHOLOGY = "cytopathology"
    FNAC = "fnac"
    BIOPSY = "biopsy"
    SURGICAL_PATHOLOGY = "surgical_pathology"
    HEMATOPATHOLOGY = "hematopathology"
    BONE_MARROW = "bone_marrow"
    MICROBIOLOGY_CULTURE = "microbiology_culture"
    MOLECULAR_PATHOLOGY = "molecular_pathology"
    IMMUNOHISTOCHEMISTRY = "immunohistochemistry"


class PathologySetting(StrEnum):
    """Drives prompt selection (`infrastructure/prompts/
    template_selector.py`) — each setting has its own independently-
    versioned prompt template set. Same five-member vocabulary, in the
    same order, as this task's own PROMPTS section — note this task
    replaces the "geriatric" member every prior AI module's own setting
    enum carries with "oncology" instead, the direct reading of this
    task's own PROMPTS list, which names "oncology" and does not name
    "geriatric" at all."""

    OUTPATIENT = "outpatient"
    INPATIENT = "inpatient"
    EMERGENCY = "emergency"
    ONCOLOGY = "oncology"
    PEDIATRIC = "pediatric"


class PathologyOutputFormat(StrEnum):
    """What shape a result is rendered into."""

    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"


class PathologyFindingCategory(StrEnum):
    """The closed vocabulary a single `PathologyFinding` is tagged with.
    `PathologyInterpretationResult.benign_features`/`.malignant_features`/
    `.atypical_findings` are computed views over one unified
    `microscopic_findings` collection filtered by this tag — see that
    value object's own docstring — rather than three separately-tracked
    collections that could drift out of sync."""

    BENIGN = "benign"
    MALIGNANT = "malignant"
    ATYPICAL = "atypical"


class PathologyInterpretationStatus(StrEnum):
    """Recorded on `GenerationSession` for this task's own AUDIT
    "interpretation status" field — named to match that wording exactly,
    the same reasoning every prior AI module's own status enum
    documents for itself."""

    COMPLETED = "completed"
    FAILED = "failed"


class PatientSex(StrEnum):
    """A same-shaped local copy of
    `app.modules.radiology_interpretation_ai.domain.enums.PatientSex`."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNSPECIFIED = "unspecified"


class PregnancyStatus(StrEnum):
    """A same-shaped local copy of
    `app.modules.radiology_interpretation_ai.domain.enums
    .PregnancyStatus` — pregnancy status is part of "Patient
    demographics" this task's own SUPPORTED INPUT section asks for."""

    NOT_PREGNANT = "not_pregnant"
    PREGNANT = "pregnant"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
