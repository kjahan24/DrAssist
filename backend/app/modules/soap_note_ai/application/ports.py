"""Application-layer ports for the AI SOAP Note Generation module, per
this task's explicit "Define SOAPGeneratorPort, SOAPPromptBuilderPort,
SOAPTemplateSelectorPort" requirement (extended here with the parser/
validator/audit/cost ports the rest of the task's pipeline needs, the
same shape `app.modules.clinical_note_ai.application.ports` establishes
for its own module).

Depends on AI Foundation's `public/` surface only (`AIMessage`), never its
`.application`/`.infrastructure` — rule: "Reuse the existing AI Foundation
... wherever possible" is satisfied by calling through its public
`AIGatewayPort`, never a provider SDK directly.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from app.modules.ai.public.dto import AIMessage
from app.modules.soap_note_ai.domain.enums import SOAPNoteOutputFormat, SOAPStyle
from app.modules.soap_note_ai.domain.value_objects import (
    GenerationSession,
    SOAPEncounterInput,
    SOAPNote,
    SOAPNoteStreamChunk,
    SOAPTemplateSet,
)


class SOAPTemplateSelectorPort(ABC):
    @abstractmethod
    def select(self, soap_style: SOAPStyle) -> SOAPTemplateSet: ...


class SOAPPromptBuilderPort(ABC):
    @abstractmethod
    async def build_messages(
        self, encounter: SOAPEncounterInput, template_set: SOAPTemplateSet
    ) -> list[AIMessage]: ...


class SOAPGeneratorPort(ABC):
    """The seam `infrastructure/generation/soap_note_generator.py`
    implements over AI Foundation's `AIGatewayPort` — use cases depend on
    this port, never on AI Foundation directly.

    `generate` returns the **raw** AI reply text, not yet a parsed
    `SOAPNote` — parsing is `SOAPNoteParserPort`'s own, separately-
    testable concern, the same split
    `app.modules.clinical_note_ai.application.ports.ClinicalNoteGeneratorPort`
    documents for itself.
    """

    @abstractmethod
    async def generate(self, encounter: SOAPEncounterInput) -> tuple[str, GenerationSession]: ...

    @abstractmethod
    def stream_generate(
        self, encounter: SOAPEncounterInput
    ) -> AsyncIterator[SOAPNoteStreamChunk]: ...


class SOAPNoteParserPort(ABC):
    @abstractmethod
    def parse(self, raw_text: str, *, output_format: SOAPNoteOutputFormat) -> SOAPNote:
        """Raises `InvalidSOAPNoteFormatError` (domain) when `raw_text`
        cannot be parsed into a `SOAPNote`."""
        ...


class SOAPNoteValidatorPort(ABC):
    @abstractmethod
    def validate(self, note: SOAPNote) -> None:
        """Raises `MissingSOAPSectionError`/`EmptySOAPResponseError`/
        `DuplicatedSOAPSectionError`/`HallucinatedPlaceholderError`/
        `InvalidMarkdownFormatError` (domain) when invalid; returns
        `None` when valid."""
        ...


class SOAPNoteAuditLoggerPort(ABC):
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
    reasoning `app.modules.clinical_note_ai.application.ports
    .CostEstimatorPort` documents for itself."""

    def estimate(
        self, *, provider: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float: ...
