"""Value objects for the AI Clinical Note Generation module's domain.

None of these reference another module's `domain`/`application`/
`infrastructure` type — every cross-module identity (organization, patient,
visit) is a plain `UUID`, and clinical content (medications, allergies,
vitals, diagnoses) is exactly what the task's own INPUT specification
calls for: free-text/simple values the caller supplies directly, not
records looked up from the Patient/Prescriptions/Visit modules. This
module never queries another module's public port for patient history —
its entire input is self-contained, per its own scope ("generates
structured clinical notes from clinical encounter input" — the input
*is* the encounter, not the patient's longitudinal record); see
`container.py`'s own scope note for the full reasoning and how this
differs from `app.modules.ai_copilot`'s `ContextBuilder`.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.modules.clinical_note_ai.domain.enums import (
    ClinicalNoteOutputFormat,
    GenerationStatus,
    NoteStyle,
)
from app.modules.clinical_note_ai.domain.exceptions import InvalidClinicalEncounterInputError
from app.shared.domain.value_object import ValueObject


@dataclass(frozen=True, slots=True)
class ClinicalEncounterInput(ValueObject):
    organization_id: UUID
    patient_id: UUID
    chief_complaint: str
    note_style: NoteStyle
    language: str = "en"
    visit_id: UUID | None = None
    history_of_present_illness: str | None = None
    symptoms: tuple[str, ...] = ()
    observations: tuple[str, ...] = ()
    physical_examination: str | None = None
    assessment: str | None = None
    plan: str | None = None
    medications: tuple[str, ...] = ()
    allergies: tuple[str, ...] = ()
    vitals: Mapping[str, str] = field(default_factory=dict)
    diagnoses: tuple[str, ...] = ()
    clinician_instructions: str | None = None
    encounter_context: str | None = None
    output_format: ClinicalNoteOutputFormat = ClinicalNoteOutputFormat.JSON

    def __post_init__(self) -> None:
        if not self.chief_complaint.strip():
            raise InvalidClinicalEncounterInputError("chief_complaint must not be blank")
        if not self.language.strip():
            raise InvalidClinicalEncounterInputError("language must not be blank")


@dataclass(frozen=True, slots=True)
class ClinicalNoteSection(ValueObject):
    name: str
    content: str


@dataclass(frozen=True, slots=True)
class ClinicalNote(ValueObject):
    """The canonical, structured generation result — always populated
    with `sections` regardless of `output_format` (a rendering-time
    concern, per `RenderClinicalNoteUseCase`'s own docstring), so "what
    the note says" and "how it's displayed" stay independently testable
    and re-renderable without a second AI call."""

    sections: tuple[ClinicalNoteSection, ...]
    raw_text: str
    output_format: ClinicalNoteOutputFormat

    def get_section(self, name: str) -> str | None:
        normalized = name.strip().lower()
        for section in self.sections:
            if section.name.strip().lower() == normalized:
                return section.content
        return None

    def has_section(self, name: str) -> bool:
        content = self.get_section(name)
        return content is not None and bool(content.strip())


@dataclass(frozen=True, slots=True)
class ClinicalNoteTemplateSet(ValueObject):
    """The three AI-Foundation-registered prompt template names (system/
    developer/user) and pinned version `TemplateSelectorPort.select`
    resolves a `NoteStyle` to — see
    `infrastructure/prompts/template_selector.py`."""

    system_template_name: str
    developer_template_name: str
    user_template_name: str
    version: int


@dataclass(frozen=True, slots=True)
class GenerationSession(ValueObject):
    """The tracked record of one generation attempt, per this task's own
    "AUDIT — Log provider, model, latency, token usage, generation
    status" requirement. `provider`/`model` are plain `str`, not AI
    Foundation's own `AIProviderType`/`AIModel` — this module's domain
    does not import even AI Foundation's *public* types (see this
    module's own docstring), so they are recorded as the strings AI
    Foundation's response already carries, read at the infrastructure
    layer where that public import is allowed
    (`infrastructure/generation/clinical_note_generator.py`)."""

    generation_id: UUID
    provider: str
    model: str
    note_style: str
    language: str
    status: GenerationStatus
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class ClinicalNoteStreamChunk(ValueObject):
    """One increment of a streamed generation — see
    `infrastructure/generation/clinical_note_generator.py`'s own
    docstring for why this is a post-hoc chunking of one complete AI
    Foundation call rather than true token-level streaming."""

    delta: str
    is_final: bool = False
