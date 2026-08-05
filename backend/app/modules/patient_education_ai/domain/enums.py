"""Enums owned by the AI Patient Education & Discharge Instructions
module's domain."""

from enum import StrEnum


class PatientEducationSetting(StrEnum):
    """Drives prompt selection (`infrastructure/prompts
    /template_selector.py`) — each setting has its own independently-
    versioned prompt template set. Six members, in the same order as
    this task's own PROMPTS section (adult/pediatric/geriatric/
    pregnancy/emergency_discharge/hospital_discharge)."""

    ADULT = "adult"
    PEDIATRIC = "pediatric"
    GERIATRIC = "geriatric"
    PREGNANCY = "pregnancy"
    EMERGENCY_DISCHARGE = "emergency_discharge"
    HOSPITAL_DISCHARGE = "hospital_discharge"


class PatientEducationOutputFormat(StrEnum):
    """What shape a result is rendered into."""

    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"


class EducationGenerationStatus(StrEnum):
    """Recorded on `GenerationSession` for this task's own AUDIT
    "education generation status" field — named to match that wording
    exactly, the same reasoning every prior AI module's own status enum
    documents for itself."""

    COMPLETED = "completed"
    FAILED = "failed"
