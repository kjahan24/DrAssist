"""Application-layer ports for the AI Differential Diagnosis module, per
this task's explicit "Define DifferentialDiagnosisGeneratorPort,
DifferentialDiagnosisPromptBuilderPort, ClinicalReasoningPort"
requirement (extended here with the template-selector/parser/validator/
audit/cost ports the rest of the task's pipeline needs — the same "named
ports plus the operationally-necessary rest" shape
`app.modules.prescription_ai.application.ports` establishes for its own
module, whose own docstring documents the identical reasoning).

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
from app.modules.differential_diagnosis_ai.domain.enums import (
    ClinicalSetting,
    DifferentialOutputFormat,
    UrgencyLevel,
)
from app.modules.differential_diagnosis_ai.domain.value_objects import (
    DifferentialDiagnosisInput,
    DifferentialDiagnosisResult,
    DifferentialDiagnosisStreamChunk,
    DifferentialDiagnosisTemplateSet,
    GenerationSession,
)


class DifferentialDiagnosisTemplateSelectorPort(ABC):
    @abstractmethod
    def select(self, clinical_setting: ClinicalSetting) -> DifferentialDiagnosisTemplateSet: ...


class DifferentialDiagnosisPromptBuilderPort(ABC):
    @abstractmethod
    async def build_messages(
        self, evidence: DifferentialDiagnosisInput, template_set: DifferentialDiagnosisTemplateSet
    ) -> list[AIMessage]: ...


class DifferentialDiagnosisGeneratorPort(ABC):
    """The seam `infrastructure/generation
    /differential_diagnosis_generator.py` implements over AI Foundation's
    `AIGatewayPort` — use cases depend on this port, never on AI
    Foundation directly.

    `generate` returns the **raw** AI reply text, not yet a parsed
    `DifferentialDiagnosisResult` — parsing is
    `DifferentialDiagnosisParserPort`'s own, separately-testable concern,
    the same split
    `app.modules.prescription_ai.application.ports.PrescriptionGeneratorPort`
    documents for itself.
    """

    @abstractmethod
    async def generate(
        self, evidence: DifferentialDiagnosisInput
    ) -> tuple[str, GenerationSession]: ...

    @abstractmethod
    def stream_generate(
        self, evidence: DifferentialDiagnosisInput
    ) -> AsyncIterator[DifferentialDiagnosisStreamChunk]: ...


class DifferentialDiagnosisParserPort(ABC):
    @abstractmethod
    def parse(
        self, raw_text: str, *, output_format: DifferentialOutputFormat
    ) -> DifferentialDiagnosisResult:
        """Raises `InvalidDifferentialResponseFormatError` (domain) when
        `raw_text` cannot be parsed into a `DifferentialDiagnosisResult`."""
        ...


class DifferentialDiagnosisValidatorPort(ABC):
    @abstractmethod
    def validate(self, result: DifferentialDiagnosisResult) -> None:
        """Raises `EmptyDifferentialResponseError`/
        `DuplicateDiagnosisError`/`InvalidConfidenceScoreError`/
        `InvalidRankingError`/`HallucinatedDiagnosisError`/
        `InconsistentReasoningError` (domain) when invalid; returns
        `None` when valid."""
        ...


class ClinicalReasoningPort(ABC):
    """This module's own deterministic clinical-reasoning seam, per this
    task's own "CLINICAL REASONING" section. Two of that section's six
    categories — "confidence ranking" and "urgency classification" — are
    partly deterministic (a candidate carrying red-flag indicators should
    never be under-triaged as `UrgencyLevel.ROUTINE`, regardless of what
    the AI itself reported), so this port supplies that floor; the
    remaining categories ("supporting evidence", "contradictory
    findings", "diagnostic uncertainty") are the AI's own semantic
    reasoning task, populated directly via
    `DifferentialDiagnosisCandidate.supporting_findings`/
    `findings_against`/`confidence_score` — the same "some categories are
    deterministic, some are inherently the model's own judgment" split
    `app.modules.prescription_ai.domain.value_objects
    .MedicationSafetyFinding`'s own docstring documents for its own six
    non-deterministic MEDICATION SAFETY categories.

    `identify_missing_information` covers the "missing information"
    reasoning category — used by `ValidateClinicalEvidenceUseCase` as
    part of its advisory pre-flight warnings (not the generation
    pipeline), the same "advisory, non-throwing" placement
    `app.modules.icd10_ai.application.use_cases.validate_clinical_context
    .ValidateClinicalContextUseCase` establishes for itself.
    """

    @abstractmethod
    def classify_minimum_urgency(
        self, *, red_flag_indicators: tuple[str, ...], confidence_score: float | None
    ) -> UrgencyLevel: ...

    @abstractmethod
    def identify_missing_information(
        self, evidence: DifferentialDiagnosisInput
    ) -> tuple[str, ...]: ...


class DifferentialDiagnosisAuditLoggerPort(ABC):
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
    reasoning `app.modules.prescription_ai.application.ports
    .CostEstimatorPort` documents for itself."""

    def estimate(
        self, *, provider: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float: ...
