"""Enums owned by the AI Clinical Note Generation module's domain."""

from enum import StrEnum


class NoteStyle(StrEnum):
    """Drives both prompt selection (`infrastructure/prompts/
    template_selector.py`) and, indirectly, generation length/tone —
    each style has its own independently-versioned prompt template set,
    per this task's "Support multiple note styles" requirement."""

    CONCISE = "concise"
    DETAILED = "detailed"
    EMERGENCY = "emergency"
    OUTPATIENT = "outpatient"
    FOLLOW_UP = "follow_up"


class ClinicalNoteOutputFormat(StrEnum):
    """What shape `RenderClinicalNoteUseCase` renders a `ClinicalNote`
    into. Distinct from `app.modules.ai_copilot.domain.enums
    .CopilotOutputFormat` — a same-shaped local copy, not a shared type,
    per this codebase's "domain code never imports across module
    boundaries" rule (see `domain/value_objects.py`'s own module
    docstring)."""

    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"


class ClinicalNoteSectionName(StrEnum):
    """The six canonical sections this task names explicitly ("including
    sections such as..."). The AI is always prompted for exactly these
    six (see `infrastructure/prompts/templates.py`) — `ClinicalNote
    .sections` itself is not restricted to only these values (a value
    object, not an enum-keyed mapping), so a future note style needing an
    extra section (e.g. emergency "Disposition") can add one without a
    schema change; only the default prompt/parser contract is fixed to
    these six today.
    """

    CHIEF_COMPLAINT = "chief_complaint"
    HISTORY_OF_PRESENT_ILLNESS = "history_of_present_illness"
    REVIEW_OF_SYSTEMS = "review_of_systems"
    PHYSICAL_EXAMINATION = "physical_examination"
    ASSESSMENT = "assessment"
    PLAN = "plan"


class GenerationStatus(StrEnum):
    """Recorded on `GenerationSession` for the "generation status" audit
    field this task asks for."""

    COMPLETED = "completed"
    FAILED = "failed"
