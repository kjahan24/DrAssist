"""Application-layer ports for the AI Pathology Interpretation module,
per this task's explicit "Create ports: PathologyInterpreterPort,
PathologyPromptBuilderPort, ClinicalCorrelationPort" requirement
(extended here with the template-selector/parser/validator/audit/cost
ports the rest of the task's pipeline needs — the same "named ports plus
the operationally-necessary rest" shape every prior AI module's own
`application/ports.py` establishes for itself).

Depends on AI Foundation's `public/` surface only (`AIMessage`), never
its `.application`/`.infrastructure` — rule: "Reuse the existing AI
Foundation... wherever possible" is satisfied by calling through its
public `AIGatewayPort`, never a provider SDK directly.

This module's genuine reuse of `app.modules.medical_reasoning_ai` is
*not* modeled as one of these ports — `application/use_cases
/interpret_pathology_report.py` depends directly on that peer module's
own public port, `MedicalReasoningAIPort`
(`app.modules.medical_reasoning_ai.public.interfaces`), the same way
`app.modules.radiology_interpretation_ai.application.use_cases
.interpret_radiology_report.InterpretRadiologyReportUseCase` already
does for itself. See `container.py`'s own module docstring for the full
reasoning.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from app.modules.ai.public.dto import AIMessage
from app.modules.pathology_interpretation_ai.domain.enums import (
    PathologyFindingCategory,
    PathologyOutputFormat,
    PathologySetting,
)
from app.modules.pathology_interpretation_ai.domain.value_objects import (
    GenerationSession,
    PathologyFinding,
    PathologyInterpretationInput,
    PathologyInterpretationResult,
    PathologyInterpretationStreamChunk,
    PathologyInterpretationTemplateSet,
)


class PathologyInterpretationTemplateSelectorPort(ABC):
    @abstractmethod
    def select(self, pathology_setting: PathologySetting) -> PathologyInterpretationTemplateSet: ...


class PathologyPromptBuilderPort(ABC):
    @abstractmethod
    async def build_messages(
        self,
        input_dto: PathologyInterpretationInput,
        template_set: PathologyInterpretationTemplateSet,
    ) -> list[AIMessage]: ...


class PathologyInterpreterPort(ABC):
    """The seam `infrastructure/generation
    /pathology_interpretation_generator.py` implements over AI
    Foundation's `AIGatewayPort` — the use case depends on this port,
    never on AI Foundation directly.

    `generate` returns the **raw** AI reply text, not yet a parsed
    `PathologyInterpretationResult` — parsing is
    `PathologyInterpretationParserPort`'s own, separately-testable
    concern.
    """

    @abstractmethod
    async def generate(
        self, input_dto: PathologyInterpretationInput
    ) -> tuple[str, GenerationSession]: ...

    @abstractmethod
    def stream_generate(
        self, input_dto: PathologyInterpretationInput
    ) -> AsyncIterator[PathologyInterpretationStreamChunk]: ...


class PathologyInterpretationParserPort(ABC):
    @abstractmethod
    def parse(
        self, raw_text: str, *, output_format: PathologyOutputFormat
    ) -> PathologyInterpretationResult:
        """Raises `InvalidPathologyInterpretationResponseFormatError`
        (domain) when `raw_text` cannot be parsed into a
        `PathologyInterpretationResult`."""
        ...


class PathologyInterpretationValidatorPort(ABC):
    @abstractmethod
    def validate(self, result: PathologyInterpretationResult) -> None:
        """Raises `DuplicatePathologyFindingError`/
        `HallucinatedPathologyFindingError`/
        `InconsistentPathologyConclusionsError`/
        `InvalidPathologyConfidenceValueError` (domain) when invalid;
        returns `None` when valid."""
        ...


class ClinicalCorrelationPort(ABC):
    """This module's own deterministic finding-correlation seam, per
    this task's own explicit `ClinicalCorrelationPort` port — a curated,
    keyword-driven scan of report text that deterministically
    *correlates* free-text microscopic language against known benign/
    malignant terminology, the same "each module defines its own local,
    necessarily-incomplete copy" precedent
    `app.modules.radiology_interpretation_ai`'s `FindingExtractionPort`
    establishes for itself, applied here to pathology-specific
    vocabulary.

    - `extract_candidate_findings` — scans a full report's `report_text`
      for curated benign/malignant keyword phrases and returns each
      match as a standalone `PathologyFinding`; used both to build
      genuinely new candidate findings (`application/services
      /finding_extraction_service.FindingExtractionService.extract`) and
      to recover findings the AI's own response may have silently
      omitted (`application/services/malignancy_assessment_service
      .MalignancyAssessmentService.derive_findings_missed_by_ai`).
    - `classify_description` — given **one** finding's own description
      text (typically an AI-reported finding), deterministically
      classifies it via the same curated keyword table; returns `None`
      when no keyword is recognized (defer entirely to the AI's own
      classification) — never a fabricated classification for language
      this port does not actually recognize.
    """

    @abstractmethod
    def extract_candidate_findings(self, report_text: str) -> tuple[PathologyFinding, ...]: ...

    @abstractmethod
    def classify_description(self, description: str) -> PathologyFindingCategory | None: ...


class PathologyInterpretationAuditLoggerPort(ABC):
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
