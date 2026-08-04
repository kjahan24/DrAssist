"""Application-layer ports for the AI ICD-10 Coding module, per this
task's explicit "Define ICD10GeneratorPort, ICD10PromptBuilderPort,
ICD10KnowledgePort" requirement (extended here with the template-
selector/parser/validator/audit/cost ports the rest of the task's
pipeline needs — the same "named ports plus the operationally-necessary
rest" shape `app.modules.soap_note_ai.application.ports` establishes for
its own module, whose own docstring documents the identical reasoning).

Depends on AI Foundation's `public/` surface only (`AIMessage`), never its
`.application`/`.infrastructure` — rule: "Reuse the existing AI
Foundation... wherever possible" is satisfied by calling through its
public `AIGatewayPort`, never a provider SDK directly.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from app.modules.ai.public.dto import AIMessage
from app.modules.icd10_ai.domain.enums import CodingSetting, ICD10OutputFormat
from app.modules.icd10_ai.domain.value_objects import (
    GenerationSession,
    ICD10CodingInput,
    ICD10StreamChunk,
    ICD10SuggestionSet,
    ICD10TemplateSet,
)


class ICD10TemplateSelectorPort(ABC):
    @abstractmethod
    def select(self, coding_setting: CodingSetting) -> ICD10TemplateSet: ...


class ICD10PromptBuilderPort(ABC):
    @abstractmethod
    async def build_messages(
        self, coding_input: ICD10CodingInput, template_set: ICD10TemplateSet
    ) -> list[AIMessage]: ...


class ICD10GeneratorPort(ABC):
    """The seam `infrastructure/generation/icd10_generator.py` implements
    over AI Foundation's `AIGatewayPort` — use cases depend on this port,
    never on AI Foundation directly.

    `generate` returns the **raw** AI reply text, not yet a parsed
    `ICD10SuggestionSet` — parsing is `ICD10SuggestionParserPort`'s own,
    separately-testable concern, the same split
    `app.modules.soap_note_ai.application.ports.SOAPGeneratorPort`
    documents for itself.
    """

    @abstractmethod
    async def generate(self, coding_input: ICD10CodingInput) -> tuple[str, GenerationSession]: ...

    @abstractmethod
    def stream_generate(
        self, coding_input: ICD10CodingInput
    ) -> AsyncIterator[ICD10StreamChunk]: ...


class ICD10SuggestionParserPort(ABC):
    @abstractmethod
    def parse(self, raw_text: str, *, output_format: ICD10OutputFormat) -> ICD10SuggestionSet:
        """Raises `InvalidICD10ResponseFormatError` (domain) when
        `raw_text` cannot be parsed into an `ICD10SuggestionSet`."""
        ...


class ICD10KnowledgePort(ABC):
    """This module's own small ICD-10-CM knowledge surface — a real
    production system would call a licensed, regularly-updated ICD-10-CM
    code database/API; this port is the seam that swaps in for one
    without the application layer (the validator, the ranking service)
    ever depending on how that lookup is actually implemented.

    Two independently useful signals, not one:

    - `is_valid_format` is a deterministic, complete structural check
      (every real ICD-10-CM code matches the same letter-digit-digit
      [+ up to 4 more alphanumeric] shape) — used by
      `ICD10SuggestionValidatorPort` as a **hard** rejection gate for
      this task's own "invalid ICD codes" validation category.
    - `lookup_canonical_name` is a **soft** signal against a necessarily
      incomplete curated reference set of common codes — used by
      `application/services/icd10_ranking_service.py` as one input to
      "clinical relevance" ranking. Returning `None` means "not in the
      curated set", not "invalid" — the validator never calls this
      method for that reason.
    """

    @abstractmethod
    def is_valid_format(self, icd10_code: str) -> bool: ...

    @abstractmethod
    def lookup_canonical_name(self, icd10_code: str) -> str | None: ...


class ICD10SuggestionValidatorPort(ABC):
    @abstractmethod
    def validate(self, suggestion_set: ICD10SuggestionSet) -> None:
        """Raises `EmptyICD10ResponseError`/`InvalidICD10CodeError`/
        `DuplicateICD10CodeError`/`HallucinatedDiagnosisError`/
        `MissingConfidenceScoreError` (domain) when invalid; returns
        `None` when valid."""
        ...


class ICD10AuditLoggerPort(ABC):
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
    reasoning `app.modules.soap_note_ai.application.ports.CostEstimatorPort`
    documents for itself."""

    def estimate(
        self, *, provider: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float: ...
