"""Enums owned by the AI SOAP Note Generation module's domain."""

from enum import StrEnum


class SOAPStyle(StrEnum):
    """Drives prompt selection (`infrastructure/prompts/
    template_selector.py`) — each style has its own independently-
    versioned prompt template set, the same "Support multiple styles"
    shape `app.modules.clinical_note_ai.domain.enums.NoteStyle`
    establishes for its own module (a distinct member set, not shared —
    SOAP's "standard" has no equivalent in clinical-note styles)."""

    CONCISE = "concise"
    STANDARD = "standard"
    DETAILED = "detailed"
    EMERGENCY = "emergency"
    FOLLOW_UP = "follow_up"


class SOAPNoteOutputFormat(StrEnum):
    """What shape `RenderSOAPNoteUseCase` renders a `SOAPNote` into. A
    same-shaped local copy of
    `app.modules.clinical_note_ai.domain.enums.ClinicalNoteOutputFormat`
    — domain code never imports across module boundaries (see
    `domain/value_objects.py`'s own module docstring)."""

    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"


class SOAPSectionName(StrEnum):
    """The four canonical SOAP sections. The AI is always prompted for
    exactly these four (see `infrastructure/prompts/templates.py`)."""

    SUBJECTIVE = "subjective"
    OBJECTIVE = "objective"
    ASSESSMENT = "assessment"
    PLAN = "plan"


class GenerationStatus(StrEnum):
    """Recorded on `GenerationSession` for the "generation status" audit
    field this task asks for."""

    COMPLETED = "completed"
    FAILED = "failed"


class PatientSex(StrEnum):
    """A closed, small vocabulary (unlike free-text `language`), worth an
    enum the same way `app.modules.patient.domain.enums.Gender` is for
    its own module — a same-*shaped*, not shared, local copy, since
    domain code never imports a peer module's domain enum."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNSPECIFIED = "unspecified"
