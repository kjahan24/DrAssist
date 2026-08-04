"""Application-layer ports for the AI Clinical Note Generation module,
per this task's explicit "Define ports for ClinicalNoteGeneratorPort,
PromptBuilderPort, TemplateSelectorPort" requirement (extended here with
the parser/validator/audit/cost ports the rest of the task's pipeline
needs, the same shape `app.modules.ai_copilot.application.ports`
establishes for its own module).

Depends on AI Foundation's `public/` surface only (`AIMessage`), never its
`.application`/`.infrastructure` — rule: "Everything must go through
AIProvider" (AI Foundation's `AIGatewayPort`).
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from app.modules.ai.public.dto import AIMessage
from app.modules.clinical_note_ai.domain.enums import ClinicalNoteOutputFormat, NoteStyle
from app.modules.clinical_note_ai.domain.value_objects import (
    ClinicalEncounterInput,
    ClinicalNote,
    ClinicalNoteStreamChunk,
    ClinicalNoteTemplateSet,
    GenerationSession,
)


class TemplateSelectorPort(ABC):
    @abstractmethod
    def select(self, note_style: NoteStyle) -> ClinicalNoteTemplateSet: ...


class PromptBuilderPort(ABC):
    @abstractmethod
    async def build_messages(
        self, encounter: ClinicalEncounterInput, template_set: ClinicalNoteTemplateSet
    ) -> list[AIMessage]: ...


class ClinicalNoteGeneratorPort(ABC):
    """The seam `infrastructure/generation/clinical_note_generator.py`
    implements over AI Foundation's `AIGatewayPort` — use cases depend on
    this port, never on AI Foundation directly, so a future non-AI-
    Foundation-backed implementation (or a test fake) is a drop-in
    replacement.

    `generate` returns the **raw** AI reply text, not yet a parsed
    `ClinicalNote` — parsing is `ClinicalNoteParserPort`'s own,
    separately-testable concern (this task's own "OUTPUT PARSER" section
    is distinct from "provider failure/timeout" error handling, which
    belongs here), and `GenerateClinicalNoteUseCase` composes the two.
    """

    @abstractmethod
    async def generate(
        self, encounter: ClinicalEncounterInput
    ) -> tuple[str, GenerationSession]: ...

    @abstractmethod
    def stream_generate(
        self, encounter: ClinicalEncounterInput
    ) -> AsyncIterator[ClinicalNoteStreamChunk]:
        """Declared as a plain (non-`async def`) method returning
        `AsyncIterator[ClinicalNoteStreamChunk]` — the same reason AI
        Foundation's own `AIProviderPort.stream_complete` uses this
        shape (see that module's own docstring): an abstract method body
        is never executed, so this signature is satisfied by either an
        `async def ...: yield ...` generator or a plain method returning
        an async-iterable object."""
        ...


class ClinicalNoteParserPort(ABC):
    @abstractmethod
    def parse(self, raw_text: str, *, output_format: ClinicalNoteOutputFormat) -> ClinicalNote:
        """Raises `InvalidClinicalNoteFormatError` (domain) when
        `raw_text` cannot be parsed into a `ClinicalNote`."""
        ...


class ClinicalNoteValidatorPort(ABC):
    @abstractmethod
    def validate(self, note: ClinicalNote) -> None:
        """Raises `MissingClinicalNoteSectionError`/`EmptyAIResponseError`/
        `HallucinatedPlaceholderError` (domain) when invalid; returns
        `None` when valid."""
        ...


class ClinicalNoteAuditLoggerPort(ABC):
    @abstractmethod
    async def log_generation(
        self, session: GenerationSession, *, organization_id: UUID, patient_id: UUID
    ) -> None: ...

    @abstractmethod
    async def log_failure(
        self,
        *,
        generation_id: UUID,
        organization_id: UUID,
        patient_id: UUID,
        stage: str,
        error_code: str,
        message: str,
    ) -> None: ...


class CostEstimatorPort(Protocol):
    """A `typing.Protocol`, not an `ABC` — the same structural-typing
    reasoning `app.modules.ai_copilot.application.ports.CostEstimatorPort`
    documents for itself: one concrete implementation
    (`infrastructure/cost/cost_estimator.py::CostEstimator`), typed here
    so a test double can satisfy it without subclassing."""

    def estimate(
        self, *, provider: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float: ...
