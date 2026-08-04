"""Application-layer ports for the AI Lab Interpretation module, per this
task's explicit "Create ports: LabInterpreterPort, LabPromptBuilderPort,
CriticalValueAnalyzerPort" requirement (extended here with the template-
selector/parser/validator/audit/cost ports the rest of the task's
pipeline needs — the same "named ports plus the operationally-necessary
rest" shape `app.modules.medical_reasoning_ai.application.ports`
establishes for its own module).

Depends on AI Foundation's `public/` surface only (`AIMessage`), never
its `.application`/`.infrastructure` — rule: "Reuse the existing AI
Foundation... wherever possible" is satisfied by calling through its
public `AIGatewayPort`, never a provider SDK directly.

This module's genuine reuse of `app.modules.medical_reasoning_ai` is
*not* modeled as one of these ports — `application/use_cases
/interpret_lab_results.py` depends directly on that peer module's own
public port, `MedicalReasoningAIPort`
(`app.modules.medical_reasoning_ai.public.interfaces`), the same way
every module in this codebase already depends directly on AI
Foundation's own `AIGatewayPort` rather than re-declaring a local
wrapper port around it. See `container.py`'s own module docstring for
the full reasoning on why this reuse is genuine (not merely pattern
reuse) for this task specifically.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from app.modules.ai.public.dto import AIMessage
from app.modules.lab_interpretation_ai.domain.enums import (
    LabFindingFlag,
    LabInterpretationOutputFormat,
    LabInterpretationSetting,
)
from app.modules.lab_interpretation_ai.domain.value_objects import (
    GenerationSession,
    LabInterpretationInput,
    LabInterpretationResult,
    LabInterpretationStreamChunk,
    LabInterpretationTemplateSet,
)


class LabInterpretationTemplateSelectorPort(ABC):
    @abstractmethod
    def select(self, lab_setting: LabInterpretationSetting) -> LabInterpretationTemplateSet: ...


class LabPromptBuilderPort(ABC):
    @abstractmethod
    async def build_messages(
        self, input_dto: LabInterpretationInput, template_set: LabInterpretationTemplateSet
    ) -> list[AIMessage]: ...


class LabInterpreterPort(ABC):
    """The seam `infrastructure/generation
    /lab_interpretation_generator.py` implements over AI Foundation's
    `AIGatewayPort` — the use case depends on this port, never on AI
    Foundation directly.

    `generate` returns the **raw** AI reply text, not yet a parsed
    `LabInterpretationResult` — parsing is
    `LabInterpretationParserPort`'s own, separately-testable concern.
    """

    @abstractmethod
    async def generate(
        self, input_dto: LabInterpretationInput
    ) -> tuple[str, GenerationSession]: ...

    @abstractmethod
    def stream_generate(
        self, input_dto: LabInterpretationInput
    ) -> AsyncIterator[LabInterpretationStreamChunk]: ...


class LabInterpretationParserPort(ABC):
    @abstractmethod
    def parse(
        self, raw_text: str, *, output_format: LabInterpretationOutputFormat
    ) -> LabInterpretationResult:
        """Raises `InvalidLabInterpretationResponseFormatError` (domain)
        when `raw_text` cannot be parsed into a `LabInterpretationResult`."""
        ...


class LabInterpretationValidatorPort(ABC):
    @abstractmethod
    def validate(self, result: LabInterpretationResult) -> None:
        """Raises `MissingLabReasoningError`/`HallucinatedLabValueError`
        (domain) when invalid; returns `None` when valid."""
        ...


class CriticalValueAnalyzerPort(ABC):
    """This module's own deterministic critical-value seam, per this
    task's own explicit `CriticalValueAnalyzerPort` port and
    `CriticalValueDetectionService` requirements — a curated,
    generic-adult reference-range table keyed by test name, the same
    "each module defines its own local, necessarily-incomplete copy"
    precedent `app.modules.icd10_ai`'s `ICD10KnowledgePort`/
    `app.modules.prescription_ai`'s `MedicationKnowledgePort` establish
    for their own modules.

    Takes primitives, not a `LabValue`/`LabFinding` — this classification
    is applied to both caller-supplied `LabValue`s (indirectly, via
    `LabTrendAnalysisService`) and AI-reported `LabFinding`s (directly,
    via `CriticalValueDetectionService.reconcile_findings`), and neither
    call site should have to construct the other value object's shape
    just to ask "is this number critical for this test?".

    Returns `None` when `test_name` is not in the curated set (defer
    entirely to the AI's own classification) or `numeric_value` is
    `None` (a qualitative result cannot be numerically classified) —
    never a fabricated classification for a test this port does not
    actually have reference data for.
    """

    @abstractmethod
    def classify(self, *, test_name: str, numeric_value: float | None) -> LabFindingFlag | None: ...


class LabInterpretationAuditLoggerPort(ABC):
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
    reasoning `app.modules.medical_reasoning_ai.application.ports
    .CostEstimatorPort` documents for itself."""

    def estimate(
        self, *, provider: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float: ...
