"""Enums owned by the AI ICD-10 Coding module's domain."""

from enum import StrEnum


class CodingSetting(StrEnum):
    """Drives prompt selection (`infrastructure/prompts/
    template_selector.py`) — each setting has its own independently-
    versioned prompt template set, the same "Support outpatient/
    emergency/inpatient/follow-up" shape
    `app.modules.soap_note_ai.domain.enums.SOAPStyle` establishes for its
    own module's style selection (a distinct member set, not shared —
    coding context is not a documentation style)."""

    OUTPATIENT = "outpatient"
    EMERGENCY = "emergency"
    INPATIENT = "inpatient"
    FOLLOW_UP = "follow_up"


class ICD10OutputFormat(StrEnum):
    """What shape a suggestion set is rendered into. A same-shaped local
    copy of `app.modules.soap_note_ai.domain.enums.SOAPNoteOutputFormat`
    — domain code never imports across module boundaries (see
    `domain/value_objects.py`'s own module docstring)."""

    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"


class DiagnosisFlag(StrEnum):
    """Primary/secondary flag this task's own OUTPUT specification
    requires on every suggestion."""

    PRIMARY = "primary"
    SECONDARY = "secondary"


class GenerationStatus(StrEnum):
    """Recorded on `GenerationSession` for the "generation status" audit
    field this task asks for."""

    COMPLETED = "completed"
    FAILED = "failed"


class PatientSex(StrEnum):
    """A closed, small vocabulary (unlike free-text `language`), worth an
    enum the same way `app.modules.soap_note_ai.domain.enums.PatientSex`
    is for its own module — a same-*shaped*, not shared, local copy,
    since domain code never imports a peer module's domain enum."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNSPECIFIED = "unspecified"
