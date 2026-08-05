"""Enums owned by the AI Radiology Interpretation module's domain."""

from enum import StrEnum


class RadiologyExaminationType(StrEnum):
    """The closed vocabulary of textual-report modalities this task's own
    SUPPORTED INPUT section names, in the same order. This module never
    interprets raw DICOM images — it interprets the *textual report* of
    one of these examinations only, per this task's own GOAL section."""

    CHEST_XRAY = "chest_xray"
    ABDOMEN_XRAY = "abdomen_xray"
    CT_BRAIN = "ct_brain"
    CT_CHEST = "ct_chest"
    CT_ABDOMEN = "ct_abdomen"
    CT_PELVIS = "ct_pelvis"
    MRI_BRAIN = "mri_brain"
    MRI_SPINE = "mri_spine"
    MRI_KNEE = "mri_knee"
    ULTRASOUND = "ultrasound"
    ECHOCARDIOGRAPHY = "echocardiography"
    MAMMOGRAPHY = "mammography"
    GENERAL = "general"


class RadiologySetting(StrEnum):
    """Drives prompt selection (`infrastructure/prompts/
    template_selector.py`) — each setting has its own independently-
    versioned prompt template set. Same five-member vocabulary, in the
    same order, as this task's own PROMPTS section, and a same-*shaped*
    (not shared) local copy of
    `app.modules.lab_interpretation_ai.domain.enums
    .LabInterpretationSetting` — domain code never imports a peer
    module's domain enum."""

    OUTPATIENT = "outpatient"
    INPATIENT = "inpatient"
    EMERGENCY = "emergency"
    PEDIATRIC = "pediatric"
    GERIATRIC = "geriatric"


class RadiologyOutputFormat(StrEnum):
    """What shape a result is rendered into."""

    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"


class RadiologyFindingCategory(StrEnum):
    """The closed vocabulary a single `RadiologyFinding` is tagged with.
    `RadiologyInterpretationResult.normal_findings`/`.abnormal_findings`/
    `.incidental_findings`/`.critical_findings`/`.important_findings` are
    computed views over one unified `findings` collection filtered by
    this tag — see that value object's own docstring — rather than five
    separately-tracked collections that could drift out of sync. Unlike
    `app.modules.lab_interpretation_ai.domain.enums.LabFindingFlag`,
    there is no "low"/"high" direction here — imaging findings are
    categorical, not magnitude-based."""

    NORMAL = "normal"
    ABNORMAL = "abnormal"
    INCIDENTAL = "incidental"
    CRITICAL = "critical"


class RadiologyInterpretationStatus(StrEnum):
    """Recorded on `GenerationSession` for this task's own AUDIT
    "interpretation status" field — named to match that wording exactly,
    the same reasoning every prior AI module's own status enum
    documents for itself."""

    COMPLETED = "completed"
    FAILED = "failed"


class PatientSex(StrEnum):
    """A same-shaped local copy of
    `app.modules.lab_interpretation_ai.domain.enums.PatientSex`."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNSPECIFIED = "unspecified"


class PregnancyStatus(StrEnum):
    """A same-shaped local copy of
    `app.modules.lab_interpretation_ai.domain.enums.PregnancyStatus` —
    pregnancy status is part of "Patient demographics" this task's own
    SUPPORTED INPUT section asks for."""

    NOT_PREGNANT = "not_pregnant"
    PREGNANT = "pregnant"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
