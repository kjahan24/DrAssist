"""Application-layer ports for the AI Medical Reasoning Engine, per this
task's explicit "Create ports: MedicalReasoningPort, EvidenceAnalyzerPort,
ConfidenceCalculatorPort, ReasoningPromptBuilderPort" requirement
(extended here with the template-selector/parser/validator/audit/cost
ports the rest of the task's pipeline needs — the same "named ports plus
the operationally-necessary rest" shape
`app.modules.differential_diagnosis_ai.application.ports` establishes for
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
from app.modules.medical_reasoning_ai.domain.enums import (
    MedicalReasoningOutputFormat,
    ReasoningSetting,
)
from app.modules.medical_reasoning_ai.domain.value_objects import (
    EvidenceItem,
    GenerationSession,
    MedicalReasoningInput,
    MedicalReasoningResult,
    MedicalReasoningStreamChunk,
    MedicalReasoningTemplateSet,
    RedFlag,
)


class MedicalReasoningTemplateSelectorPort(ABC):
    @abstractmethod
    def select(self, reasoning_setting: ReasoningSetting) -> MedicalReasoningTemplateSet: ...


class ReasoningPromptBuilderPort(ABC):
    @abstractmethod
    async def build_messages(
        self, evidence: MedicalReasoningInput, template_set: MedicalReasoningTemplateSet
    ) -> list[AIMessage]: ...


class MedicalReasoningPort(ABC):
    """The seam `infrastructure/generation/medical_reasoning_generator.py`
    implements over AI Foundation's `AIGatewayPort` — the use case depends
    on this port, never on AI Foundation directly.

    `generate` returns the **raw** AI reply text, not yet a parsed
    `MedicalReasoningResult` — parsing is `MedicalReasoningParserPort`'s
    own, separately-testable concern, the same split
    `app.modules.differential_diagnosis_ai.application.ports
    .DifferentialDiagnosisGeneratorPort` documents for itself.
    """

    @abstractmethod
    async def generate(self, evidence: MedicalReasoningInput) -> tuple[str, GenerationSession]: ...

    @abstractmethod
    def stream_generate(
        self, evidence: MedicalReasoningInput
    ) -> AsyncIterator[MedicalReasoningStreamChunk]: ...


class MedicalReasoningParserPort(ABC):
    @abstractmethod
    def parse(
        self, raw_text: str, *, output_format: MedicalReasoningOutputFormat
    ) -> MedicalReasoningResult:
        """Raises `InvalidMedicalReasoningResponseFormatError` (domain)
        when `raw_text` cannot be parsed into a `MedicalReasoningResult`."""
        ...


class MedicalReasoningValidatorPort(ABC):
    @abstractmethod
    def validate(self, result: MedicalReasoningResult) -> None:
        """Raises `EmptyReasoningResponseError`/`MissingReasoningError`/
        `DuplicateEvidenceError`/`InvalidConfidenceValueError`/
        `HallucinatedReasoningPlaceholderError`/
        `InconsistentRecommendationsError` (domain) when invalid; returns
        `None` when valid."""
        ...


class EvidenceAnalyzerPort(ABC):
    """This module's own deterministic evidence-analysis seam, per this
    task's own "REASONING ENGINE" section. Backs
    `application/services/evidence_analysis_service.EvidenceAnalysisService`,
    which owns the pure (port-free) parts of that section — conflicting-
    evidence detection and de-duplication need no external knowledge, so
    they live directly on the service; only the three genuinely
    knowledge-dependent capabilities are ports:

    - `weight_evidence_item` — "evidence weighting": adjusts (never
      replaces) an `EvidenceItem`'s AI-reported weight using deterministic
      signals (e.g. objective/measurable language carries more evidentiary
      weight than purely subjective narrative).
    - `identify_missing_information` — "missing-information analysis":
      the same "advisory, evidence-driven completeness check" shape
      `app.modules.differential_diagnosis_ai.application.ports
      .ClinicalReasoningPort.identify_missing_information` establishes for
      its own module, generalized here to this module's broader evidence
      surface.
    - `compute_risk_score` — "risk scoring": a single aggregate signal
      from `risk_factors` and `red_flags`, consumed by
      `EvidenceAnalysisService.prioritize_red_flags` to drive "red flag
      prioritization" (escalating a red flag's `RedFlagPriority` when
      overall risk is high) — the same "deterministic floor applied only
      after the AI's own output already passed validation" enrichment
      shape `app.modules.differential_diagnosis_ai.application.services
      .clinical_reasoning_service.ClinicalReasoningService
      .upgrade_urgency_levels` establishes for its own module.
    """

    @abstractmethod
    def weight_evidence_item(self, item: EvidenceItem) -> EvidenceItem: ...

    @abstractmethod
    def identify_missing_information(self, evidence: MedicalReasoningInput) -> tuple[str, ...]: ...

    @abstractmethod
    def compute_risk_score(
        self, *, risk_factors: tuple[str, ...], red_flags: tuple[RedFlag, ...]
    ) -> float: ...


class ConfidenceCalculatorPort(ABC):
    """This module's own deterministic confidence-scoring seam, per this
    task's own "confidence scoring" and "uncertainty estimation"
    REASONING ENGINE requirements. Backs `application/services
    .confidence_scoring_service.ConfidenceScoringService`.

    Applied independently to each of the three confidence dimensions this
    task's own OUTPUT specification names ("Clinical Confidence",
    "Diagnostic Confidence", "Therapeutic Confidence") — when the AI
    reports a value for a dimension, that value is trusted as-is (already
    range-validated by `MedicalReasoningValidatorPort`); when it does not,
    this port computes a deterministic fallback from the surrounding
    evidence counts rather than leaving the dimension unpopulated.
    """

    @abstractmethod
    def calculate_confidence(
        self,
        *,
        ai_reported: float | None,
        supporting_count: int,
        contradicting_count: int,
        missing_information_count: int,
    ) -> float: ...


class MedicalReasoningAuditLoggerPort(ABC):
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
    reasoning `app.modules.differential_diagnosis_ai.application.ports
    .CostEstimatorPort` documents for itself."""

    def estimate(
        self, *, provider: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float: ...
