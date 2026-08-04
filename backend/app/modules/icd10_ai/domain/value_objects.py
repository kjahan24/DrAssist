"""Value objects for the AI ICD-10 Coding module's domain.

None of these reference another module's `domain`/`application`/
`infrastructure` type — every cross-module identity (organization,
patient, visit) is a plain `UUID`, and clinical content (chief complaint,
HPI, symptoms, ROS, physical exam, assessment, plan, clinical note text,
SOAP note text, existing diagnoses) is exactly what the task's own INPUT
specification calls for: values the caller supplies directly, not records
looked up from the Clinical Note AI/SOAP Note AI/Patient modules. This
module never queries another module's public port — its entire input is
self-contained clinical context, the same design
`app.modules.soap_note_ai.domain.value_objects` establishes for itself
(see that module's own module docstring for the full reasoning, which
applies identically here).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.modules.icd10_ai.domain.enums import (
    CodingSetting,
    DiagnosisFlag,
    GenerationStatus,
    ICD10OutputFormat,
    PatientSex,
)
from app.modules.icd10_ai.domain.exceptions import InvalidClinicalContextError
from app.shared.domain.value_object import ValueObject

_MAX_PLAUSIBLE_AGE = 150


@dataclass(frozen=True, slots=True)
class ICD10CodingInput(ValueObject):
    organization_id: UUID
    patient_id: UUID
    chief_complaint: str
    coding_setting: CodingSetting
    language: str = "en"
    visit_id: UUID | None = None
    history_of_present_illness: str | None = None
    symptoms: tuple[str, ...] = ()
    review_of_systems: str | None = None
    physical_examination: str | None = None
    assessment: str | None = None
    plan: str | None = None
    clinical_note: str | None = None
    soap_note: str | None = None
    existing_diagnoses: tuple[str, ...] = ()
    visit_context: str | None = None
    patient_age: int | None = None
    patient_sex: PatientSex | None = None
    output_format: ICD10OutputFormat = ICD10OutputFormat.JSON

    def __post_init__(self) -> None:
        if not self.chief_complaint.strip():
            raise InvalidClinicalContextError("chief_complaint must not be blank")
        if not self.language.strip():
            raise InvalidClinicalContextError("language must not be blank")
        if self.patient_age is not None and not (0 <= self.patient_age <= _MAX_PLAUSIBLE_AGE):
            raise InvalidClinicalContextError(
                f"patient_age must be between 0 and {_MAX_PLAUSIBLE_AGE} when given"
            )


@dataclass(frozen=True, slots=True)
class ICD10Suggestion(ValueObject):
    """One coded diagnosis suggestion, per this task's own OUTPUT
    specification: "ICD-10 Code, Diagnosis Name, Confidence Score,
    Clinical Reasoning, Supporting Evidence, Primary/Secondary flag".

    `confidence_score` is nullable — a missing or unparseable confidence
    value from the AI's response is not a parse failure (the rest of the
    suggestion may still be usable), it is a **validation** failure per
    this task's own "missing confidence scores" category
    (`infrastructure/validation/icd10_suggestion_validator.py` raises
    `MissingConfidenceScoreError` for `None` or out-of-[0.0, 1.0] values)
    — the same "missing becomes an empty/None placeholder at parse time;
    the validator is what actually rejects it" split
    `app.modules.soap_note_ai.infrastructure.parsing.soap_note_parser`
    documents for its own missing-section handling.
    """

    icd10_code: str
    diagnosis_name: str
    confidence_score: float | None
    clinical_reasoning: str
    supporting_evidence: str
    flag: DiagnosisFlag


@dataclass(frozen=True, slots=True)
class ICD10SuggestionSet(ValueObject):
    """The canonical, structured generation result — always populated
    with `suggestions` regardless of `output_format` (a rendering-time
    concern, per `application/services/icd10_suggestion_renderer.py`'s
    own docstring), the same "generation produces structure; rendering
    produces presentation" split
    `app.modules.soap_note_ai.domain.value_objects.SOAPNote` establishes
    for itself."""

    suggestions: tuple[ICD10Suggestion, ...]
    raw_text: str
    output_format: ICD10OutputFormat

    @property
    def is_empty(self) -> bool:
        return len(self.suggestions) == 0

    @property
    def primary_suggestions(self) -> tuple[ICD10Suggestion, ...]:
        return tuple(s for s in self.suggestions if s.flag is DiagnosisFlag.PRIMARY)

    @property
    def secondary_suggestions(self) -> tuple[ICD10Suggestion, ...]:
        return tuple(s for s in self.suggestions if s.flag is DiagnosisFlag.SECONDARY)


@dataclass(frozen=True, slots=True)
class ICD10TemplateSet(ValueObject):
    """The three AI-Foundation-registered prompt template names (system/
    developer/user) and pinned version `ICD10TemplateSelectorPort.select`
    resolves a `CodingSetting` to — see
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
    coding_setting: str
    language: str
    status: GenerationStatus
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class ICD10StreamChunk(ValueObject):
    """One increment of a streamed generation — see
    `infrastructure/generation/icd10_generator.py`'s own docstring for
    why this is a post-hoc chunking of one complete AI Foundation call
    rather than true token-level streaming."""

    delta: str
    is_final: bool = False
