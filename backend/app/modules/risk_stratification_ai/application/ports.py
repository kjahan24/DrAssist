"""Application-layer ports for the AI Risk Stratification & Early
Warning Score module, per this task's explicit "Create ports:
RiskScoringPort, EarlyWarningPort, ClinicalRiskPort" requirement —
extended here with the generation/prompt/parsing/validation/audit/cost/
template-selection ports the rest of the task's pipeline needs, the same
"named ports plus the operationally-necessary rest" shape every prior AI
module's own `application/ports.py` establishes for itself
(`app.modules.drug_interaction_ai.application.ports` is the most
directly analogous precedent, itself naming four explicit ports plus a
prefixed operational set). This task names no "XxxInterpreterPort"/
"XxxPromptBuilderPort" pair of its own, so the operationally-necessary
generation/prompt-building ports are named with a
`RiskStratificationAnalysis` prefix — deliberately distinct from the
three explicitly-named ports below.

Depends on AI Foundation's `public/` surface only (`AIMessage`), never
its `.application`/`.infrastructure` — rule: "Reuse the existing AI
Foundation... wherever possible" is satisfied by calling through its
public `AIGatewayPort`, never a provider SDK directly.

This module's genuine reuse of `app.modules.medical_reasoning_ai` is
*not* modeled as one of these ports — `application/use_cases
/analyze_patient_risk.py` depends directly on that peer module's own
public port, `MedicalReasoningAIPort`
(`app.modules.medical_reasoning_ai.public.interfaces`), the same way
every prior interpretation-AI module's own use case already does for
itself. See `container.py`'s own module docstring for the full
reasoning, including why no other peer AI module's public port
(`LabInterpreterPort`/`RadiologyInterpreterPort`/`PathologyInterpreterPort`)
is called into directly — this module accepts their already-generated
summaries as plain `str | None` input fields instead (see
`domain/value_objects.py`'s own module docstring).
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from app.modules.ai.public.dto import AIMessage
from app.modules.risk_stratification_ai.domain.enums import (
    RiskCategory,
    RiskStratificationOutputFormat,
    RiskStratificationSetting,
)
from app.modules.risk_stratification_ai.domain.value_objects import (
    GenerationSession,
    LabValue,
    RiskScore,
    RiskStratificationInput,
    RiskStratificationResult,
    RiskStratificationStreamChunk,
    RiskStratificationTemplateSet,
    VitalSigns,
)


class RiskStratificationAnalysisTemplateSelectorPort(ABC):
    @abstractmethod
    def select(self, risk_setting: RiskStratificationSetting) -> RiskStratificationTemplateSet: ...


class RiskStratificationAnalysisPromptBuilderPort(ABC):
    @abstractmethod
    async def build_messages(
        self,
        input_dto: RiskStratificationInput,
        template_set: RiskStratificationTemplateSet,
    ) -> list[AIMessage]: ...


class RiskStratificationAnalysisGeneratorPort(ABC):
    """The seam `infrastructure/generation
    /risk_stratification_generator.py` implements over AI Foundation's
    `AIGatewayPort` — the use case depends on this port, never on AI
    Foundation directly.

    `generate` returns the **raw** AI reply text, not yet a parsed
    `RiskStratificationResult` — parsing is
    `RiskStratificationAnalysisParserPort`'s own, separately-testable
    concern.
    """

    @abstractmethod
    async def generate(
        self, input_dto: RiskStratificationInput
    ) -> tuple[str, GenerationSession]: ...

    @abstractmethod
    def stream_generate(
        self, input_dto: RiskStratificationInput
    ) -> AsyncIterator[RiskStratificationStreamChunk]: ...


class RiskStratificationAnalysisParserPort(ABC):
    @abstractmethod
    def parse(
        self, raw_text: str, *, output_format: RiskStratificationOutputFormat
    ) -> RiskStratificationResult:
        """Raises `InvalidRiskStratificationResponseFormatError` (domain)
        when `raw_text` cannot be parsed into a
        `RiskStratificationResult`."""
        ...


class RiskStratificationAnalysisValidatorPort(ABC):
    @abstractmethod
    def validate(
        self, result: RiskStratificationResult, input_dto: RiskStratificationInput
    ) -> None:
        """Raises `InvalidRiskScoreError`/`HallucinatedRiskFactorError`/
        `InvalidRiskConfidenceValueError` (domain) when invalid; returns
        `None` when valid."""
        ...


class RiskScoringPort(ABC):
    """This task's own explicitly-named deterministic clinical-score
    seam — unlike every prior AI module's own curated-knowledge ports,
    this one computes REAL, standardized, publicly-documented clinical
    algorithms (NEWS2, MEWS, qSOFA) directly from `VitalSigns`, rather
    than looking values up in a necessarily-incomplete reference table —
    a genuine departure from the "necessarily incomplete curated table"
    precedent every prior AI module's own knowledge-base port
    establishes for itself, justified because these three scores are
    precise, fully-specified public formulas, not fuzzy domain
    knowledge.

    `compute_sofa_simplified` is the one exception: real SOFA needs a
    PaO2/FiO2 ratio, MAP/vasopressor dose, bilirubin, platelet count, and
    Glasgow Coma Scale — data this task's own SUPPORTED INPUT list does
    not guarantee is ever available in that exact form. This method
    computes an explicitly-labeled, documented **simplified proxy** (see
    `infrastructure/clinical_scoring
    /standard_risk_scoring_calculator.py`'s own module docstring for the
    exact substitution table) over a 0-8 range, not the real 0-24 SOFA
    range — a deliberate, task-requested simplification ("SOFA
    (simplified)" is this task's own literal wording), not a clinically
    accurate SOFA implementation.

    Each method returns `None`, never a fabricated partial score, when
    `vital_signs` (and, for `compute_sofa_simplified`, `lab_values`)
    lacks the specific parameters that score requires.
    """

    @abstractmethod
    def compute_news2(self, vital_signs: VitalSigns) -> RiskScore | None: ...

    @abstractmethod
    def compute_mews(self, vital_signs: VitalSigns) -> RiskScore | None: ...

    @abstractmethod
    def compute_qsofa(self, vital_signs: VitalSigns) -> RiskScore | None: ...

    @abstractmethod
    def compute_sofa_simplified(
        self, vital_signs: VitalSigns, lab_values: tuple[LabValue, ...]
    ) -> RiskScore | None: ...


class EarlyWarningPort(ABC):
    """This task's own explicitly-named deterministic early-warning
    seam — the standard NEWS2-style clinical rule that a single grossly
    abnormal parameter warrants urgent review even when the aggregate
    score is unremarkable, plus a simple score-to-urgency mapping used
    to populate this task's own "Suggested Escalation" OUTPUT field
    deterministically rather than trusting the AI's own escalation
    wording alone.
    """

    @abstractmethod
    def identify_single_parameter_triggers(self, vital_signs: VitalSigns) -> tuple[str, ...]: ...

    @abstractmethod
    def classify_escalation_urgency(self, risk_score: RiskScore) -> str | None: ...


class ClinicalRiskPort(ABC):
    """This task's own explicitly-named deterministic risk-factor seam —
    covering the ten AI-assessed `RiskCategory` members that have no
    standardized public formula (sepsis/AKI/respiratory deterioration/
    cardiovascular/stroke/bleeding/fall/readmission/mortality/general
    deterioration risk): a curated, necessarily-incomplete reference
    table of diagnosis/history/medication/lab keywords, the same "each
    module defines its own local, necessarily-incomplete copy" precedent
    every prior AI module's own knowledge-base port establishes for
    itself. Returns `None` when it recognizes no risk factors for the
    given category from the given context, rather than fabricating a
    score.
    """

    @abstractmethod
    def identify_risk_factors(
        self,
        category: RiskCategory,
        *,
        diagnoses: tuple[str, ...],
        medical_history: tuple[str, ...],
        current_medications: tuple[str, ...],
        lab_values: tuple[LabValue, ...],
        patient_age: int | None,
    ) -> RiskScore | None: ...


class RiskStratificationAnalysisAuditLoggerPort(ABC):
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
