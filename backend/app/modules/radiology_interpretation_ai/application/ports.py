"""Application-layer ports for the AI Radiology Interpretation module,
per this task's explicit "Create ports: RadiologyInterpreterPort,
RadiologyPromptBuilderPort, FindingExtractionPort" requirement (extended
here with the template-selector/parser/validator/audit/cost ports the
rest of the task's pipeline needs — the same "named ports plus the
operationally-necessary rest" shape every prior AI module's own
`application/ports.py` establishes for itself).

Depends on AI Foundation's `public/` surface only (`AIMessage`), never
its `.application`/`.infrastructure` — rule: "Reuse the existing AI
Foundation... wherever possible" is satisfied by calling through its
public `AIGatewayPort`, never a provider SDK directly.

This module's genuine reuse of `app.modules.medical_reasoning_ai` is
*not* modeled as one of these ports — `application/use_cases
/interpret_radiology_report.py` depends directly on that peer module's
own public port, `MedicalReasoningAIPort`
(`app.modules.medical_reasoning_ai.public.interfaces`), the same way
`app.modules.lab_interpretation_ai.application.use_cases
.interpret_lab_results.InterpretLabResultsUseCase` already does for
itself, and the same way every module in this codebase already depends
directly on AI Foundation's own `AIGatewayPort` rather than re-declaring
a local wrapper port around it. See `container.py`'s own module docstring
for the full reasoning.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from app.modules.ai.public.dto import AIMessage
from app.modules.radiology_interpretation_ai.domain.enums import (
    RadiologyFindingCategory,
    RadiologyOutputFormat,
    RadiologySetting,
)
from app.modules.radiology_interpretation_ai.domain.value_objects import (
    GenerationSession,
    RadiologyFinding,
    RadiologyInterpretationInput,
    RadiologyInterpretationResult,
    RadiologyInterpretationStreamChunk,
    RadiologyInterpretationTemplateSet,
)


class RadiologyInterpretationTemplateSelectorPort(ABC):
    @abstractmethod
    def select(self, radiology_setting: RadiologySetting) -> RadiologyInterpretationTemplateSet: ...


class RadiologyPromptBuilderPort(ABC):
    @abstractmethod
    async def build_messages(
        self,
        input_dto: RadiologyInterpretationInput,
        template_set: RadiologyInterpretationTemplateSet,
    ) -> list[AIMessage]: ...


class RadiologyInterpreterPort(ABC):
    """The seam `infrastructure/generation
    /radiology_interpretation_generator.py` implements over AI
    Foundation's `AIGatewayPort` — the use case depends on this port,
    never on AI Foundation directly.

    `generate` returns the **raw** AI reply text, not yet a parsed
    `RadiologyInterpretationResult` — parsing is
    `RadiologyInterpretationParserPort`'s own, separately-testable
    concern.
    """

    @abstractmethod
    async def generate(
        self, input_dto: RadiologyInterpretationInput
    ) -> tuple[str, GenerationSession]: ...

    @abstractmethod
    def stream_generate(
        self, input_dto: RadiologyInterpretationInput
    ) -> AsyncIterator[RadiologyInterpretationStreamChunk]: ...


class RadiologyInterpretationParserPort(ABC):
    @abstractmethod
    def parse(
        self, raw_text: str, *, output_format: RadiologyOutputFormat
    ) -> RadiologyInterpretationResult:
        """Raises `InvalidRadiologyInterpretationResponseFormatError`
        (domain) when `raw_text` cannot be parsed into a
        `RadiologyInterpretationResult`."""
        ...


class RadiologyInterpretationValidatorPort(ABC):
    @abstractmethod
    def validate(self, result: RadiologyInterpretationResult) -> None:
        """Raises `DuplicateRadiologyFindingError`/
        `HallucinatedRadiologyFindingError`/
        `InconsistentRadiologyRecommendationsError`/
        `InvalidRadiologyConfidenceValueError` (domain) when invalid;
        returns `None` when valid."""
        ...


class FindingExtractionPort(ABC):
    """This module's own deterministic finding-extraction seam, per this
    task's own explicit `FindingExtractionPort` port and
    `FindingExtractionService`/`CriticalFindingDetectionService`
    requirements — a curated, keyword-driven scan of report text, the
    same "each module defines its own local, necessarily-incomplete
    copy" precedent `app.modules.lab_interpretation_ai`'s
    `CriticalValueAnalyzerPort` establishes for numeric lab values,
    applied here to free text instead of numeric ranges.

    - `extract_candidate_findings` — scans a full report's `report_text`
      for curated normal/critical keyword phrases and returns each match
      as a standalone `RadiologyFinding`; used both to build genuinely
      new candidate findings (`FindingExtractionService.extract`) and to
      recover findings the AI's own response may have silently omitted
      (`CriticalFindingDetectionService.derive_findings_missed_by_ai`).
    - `classify_description` — given **one** finding's own description
      text (typically an AI-reported finding), deterministically
      classifies it via the same curated keyword table; returns `None`
      when no keyword is recognized (defer entirely to the AI's own
      classification) — never a fabricated classification for language
      this port does not actually recognize.
    """

    @abstractmethod
    def extract_candidate_findings(self, report_text: str) -> tuple[RadiologyFinding, ...]: ...

    @abstractmethod
    def classify_description(self, description: str) -> RadiologyFindingCategory | None: ...


class RadiologyInterpretationAuditLoggerPort(ABC):
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
    reasoning every prior AI module's own `CostEstimatorPort` documents
    for itself."""

    def estimate(
        self, *, provider: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float: ...
