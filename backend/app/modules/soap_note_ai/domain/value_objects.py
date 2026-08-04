"""Value objects for the AI SOAP Note Generation module's domain.

None of these reference another module's `domain`/`application`/
`infrastructure` type — every cross-module identity (organization,
patient, visit) is a plain `UUID`, and clinical content (medications,
allergies, vitals, diagnoses, symptoms) is exactly what the task's own
INPUT specification calls for: values the caller supplies directly, not
records looked up from the Patient/Prescriptions/Visit modules. This
module never queries another module's public port — its entire input is
self-contained encounter data, the same design
`app.modules.clinical_note_ai.domain.value_objects` establishes for
itself (see that module's own module docstring for the full reasoning,
which applies identically here).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.modules.soap_note_ai.domain.enums import (
    GenerationStatus,
    PatientSex,
    SOAPNoteOutputFormat,
    SOAPStyle,
)
from app.modules.soap_note_ai.domain.exceptions import InvalidSOAPEncounterInputError
from app.shared.domain.value_object import ValueObject

_MAX_PLAUSIBLE_AGE = 150


@dataclass(frozen=True, slots=True)
class SOAPEncounterInput(ValueObject):
    organization_id: UUID
    patient_id: UUID
    chief_complaint: str
    soap_style: SOAPStyle
    language: str = "en"
    visit_id: UUID | None = None
    history_of_present_illness: str | None = None
    symptoms: tuple[str, ...] = ()
    review_of_systems: str | None = None
    physical_examination: str | None = None
    vitals: Mapping[str, str] = field(default_factory=dict)
    medications: tuple[str, ...] = ()
    allergies: tuple[str, ...] = ()
    diagnoses: tuple[str, ...] = ()
    assessment: str | None = None
    plan: str | None = None
    clinician_instructions: str | None = None
    encounter_context: str | None = None
    patient_age: int | None = None
    patient_sex: PatientSex | None = None
    visit_type: str | None = None
    output_format: SOAPNoteOutputFormat = SOAPNoteOutputFormat.JSON

    def __post_init__(self) -> None:
        if not self.chief_complaint.strip():
            raise InvalidSOAPEncounterInputError("chief_complaint must not be blank")
        if not self.language.strip():
            raise InvalidSOAPEncounterInputError("language must not be blank")
        if self.patient_age is not None and not (0 <= self.patient_age <= _MAX_PLAUSIBLE_AGE):
            raise InvalidSOAPEncounterInputError(
                f"patient_age must be between 0 and {_MAX_PLAUSIBLE_AGE}"
            )


@dataclass(frozen=True, slots=True)
class SOAPSection(ValueObject):
    name: str
    content: str


@dataclass(frozen=True, slots=True)
class SOAPNote(ValueObject):
    """The canonical, structured generation result — always populated
    with `sections` regardless of `output_format` (a rendering-time
    concern, per `RenderSOAPNoteUseCase`'s own docstring), the same
    "generation produces structure; rendering produces presentation"
    split `app.modules.clinical_note_ai.domain.value_objects.ClinicalNote`
    establishes for itself."""

    sections: tuple[SOAPSection, ...]
    raw_text: str
    output_format: SOAPNoteOutputFormat

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
class SOAPTemplateSet(ValueObject):
    """The three AI-Foundation-registered prompt template names (system/
    developer/user) and pinned version `SOAPTemplateSelectorPort.select`
    resolves a `SOAPStyle` to — see
    `infrastructure/prompts/template_selector.py`."""

    system_template_name: str
    developer_template_name: str
    user_template_name: str
    version: int


@dataclass(frozen=True, slots=True)
class GenerationSession(ValueObject):
    """The tracked record of one generation attempt, per this task's own
    "AUDIT — Record provider, model, latency, token usage, generation
    status" requirement. `provider`/`model` are plain `str`, not AI
    Foundation's own `AIProviderType`/`AIModel` — this module's domain
    does not import even AI Foundation's *public* types (see this
    module's own docstring)."""

    generation_id: UUID
    provider: str
    model: str
    soap_style: str
    language: str
    status: GenerationStatus
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class SOAPNoteStreamChunk(ValueObject):
    """One increment of a streamed generation — see
    `infrastructure/generation/soap_note_generator.py`'s own docstring
    for why this is a post-hoc chunking of one complete AI Foundation
    call rather than true token-level streaming."""

    delta: str
    is_final: bool = False
