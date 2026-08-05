"""Application-layer ports for the AI Drug Interaction & Medication
Safety module, per this task's explicit "Create ports: DrugInteractionPort,
MedicationSafetyPort, DoseAdjustmentPort, InteractionEvidencePort"
requirement — extended here with the generation/prompt/parsing/
validation/audit/cost/template-selection ports the rest of the task's
pipeline needs, the same "named ports plus the operationally-necessary
rest" shape every prior AI module's own `application/ports.py`
establishes for itself. Unlike every prior module, this task names no
"XxxInterpreterPort"/"XxxPromptBuilderPort" pair of its own, so the
operationally-necessary generation/prompt-building ports are named with
a `DrugSafetyAnalysis` prefix — deliberately distinct from the four
explicitly-named ports above (`DrugInteractionPort` and
`MedicationSafetyPort` are already taken names; reusing either for the
LLM-calling seam would be confusing) — this module ends up with eleven
ports in total, the richest port surface of any AI module in this
codebase, matching this task's own unusually rich DETECT/APPLICATION/
PORTS sections.

Depends on AI Foundation's `public/` surface only (`AIMessage`), never
its `.application`/`.infrastructure` — rule: "Reuse the existing AI
Foundation... wherever possible" is satisfied by calling through its
public `AIGatewayPort`, never a provider SDK directly.

This module's genuine reuse of `app.modules.medical_reasoning_ai` is
*not* modeled as one of these ports — `application/use_cases
/analyze_medication_safety.py` depends directly on that peer module's
own public port, `MedicalReasoningAIPort`
(`app.modules.medical_reasoning_ai.public.interfaces`), the same way
every prior interpretation-AI module's own use case already does for
itself. See `container.py`'s own module docstring for the full
reasoning, including why `app.modules.prescription_ai
.public.interfaces.PrescriptionAIPort.analyze_medication_safety` — the
one standalone capability among every reused module's own public
surface that looked most directly relevant — is not called into either.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from app.modules.ai.public.dto import AIMessage
from app.modules.drug_interaction_ai.domain.enums import (
    DrugInteractionOutputFormat,
    DrugInteractionSetting,
    EvidenceLevel,
    LactationStatus,
    PregnancyStatus,
    SafetyIssueCategory,
)
from app.modules.drug_interaction_ai.domain.value_objects import (
    DrugInteractionAnalysisInput,
    DrugInteractionAnalysisResult,
    DrugInteractionStreamChunk,
    DrugInteractionTemplateSet,
    GenerationSession,
    MedicationEntry,
    SafetyIssue,
)


class DrugSafetyAnalysisTemplateSelectorPort(ABC):
    @abstractmethod
    def select(self, medication_setting: DrugInteractionSetting) -> DrugInteractionTemplateSet: ...


class DrugSafetyAnalysisPromptBuilderPort(ABC):
    @abstractmethod
    async def build_messages(
        self, input_dto: DrugInteractionAnalysisInput, template_set: DrugInteractionTemplateSet
    ) -> list[AIMessage]: ...


class DrugSafetyAnalysisGeneratorPort(ABC):
    """The seam `infrastructure/generation
    /drug_safety_analysis_generator.py` implements over AI Foundation's
    `AIGatewayPort` — the use case depends on this port, never on AI
    Foundation directly.

    `generate` returns the **raw** AI reply text, not yet a parsed
    `DrugInteractionAnalysisResult` — parsing is
    `DrugSafetyAnalysisParserPort`'s own, separately-testable concern.
    """

    @abstractmethod
    async def generate(
        self, input_dto: DrugInteractionAnalysisInput
    ) -> tuple[str, GenerationSession]: ...

    @abstractmethod
    def stream_generate(
        self, input_dto: DrugInteractionAnalysisInput
    ) -> AsyncIterator[DrugInteractionStreamChunk]: ...


class DrugSafetyAnalysisParserPort(ABC):
    @abstractmethod
    def parse(
        self, raw_text: str, *, output_format: DrugInteractionOutputFormat
    ) -> DrugInteractionAnalysisResult:
        """Raises `InvalidDrugInteractionResponseFormatError` (domain)
        when `raw_text` cannot be parsed into a
        `DrugInteractionAnalysisResult`."""
        ...


class DrugSafetyAnalysisValidatorPort(ABC):
    @abstractmethod
    def validate(
        self, result: DrugInteractionAnalysisResult, input_dto: DrugInteractionAnalysisInput
    ) -> None:
        """Raises `UnknownMedicationError`/`HallucinatedInteractionError`/
        `InvalidDrugInteractionConfidenceValueError`/
        `MissingInteractionEvidenceError` (domain) when invalid; returns
        `None` when valid. Takes `input_dto` too (unlike every prior AI
        module's own validator) — "unknown medications" can only be
        checked against the medications the caller actually supplied."""
        ...


class DrugInteractionPort(ABC):
    """This task's own explicitly-named deterministic pairwise-
    interaction seam — a curated reference table of well-known drug-drug
    interaction pairs, the same "each module defines its own local,
    necessarily-incomplete copy" precedent every prior AI module's own
    knowledge-base port establishes for itself.

    Given two drug names, deterministically returns a `SafetyIssue`
    (category always `SafetyIssueCategory.DRUG_DRUG_INTERACTION`) when
    the pair is recognized, or `None` when it is not — never a
    fabricated interaction for a pair this port does not actually have
    reference data for.
    """

    @abstractmethod
    def check_pairwise_interaction(self, drug_a: str, drug_b: str) -> SafetyIssue | None: ...


class MedicationSafetyPort(ABC):
    """This task's own explicitly-named deterministic medication-safety
    seam — covering drug-allergy/drug-disease/pregnancy/lactation/age-
    related risk, pharmacologic risk flags (QT prolongation, serotonin
    syndrome, bleeding, nephrotoxicity, hepatotoxicity risk),
    contraindications, and black box warnings: eleven of this task's own
    eighteen DETECT categories, all sharing the same "look this
    medication up against curated reference data" shape.

    - `check_patient_context_risks` — given one medication and the
      patient-specific context this task's own SUPPORTED INPUT section
      names (allergies, medical conditions, pregnancy/lactation status,
      age), returns every applicable `SafetyIssue` from a curated
      reference table (drug-allergy cross-reactivity, drug-disease
      contraindication, pregnancy/lactation risk category, Beers-list-
      style high-risk-elderly and pediatric-unsafe medication flags).
    - `classify_pharmacologic_risk_flags` — given one medication,
      returns the subset of `SafetyIssueCategory.QT_PROLONGATION_RISK`/
      `SEROTONIN_SYNDROME_RISK`/`BLEEDING_RISK`/`NEPHROTOXICITY_RISK`/
      `HEPATOTOXICITY_RISK` a curated reference table recognizes for it.
    - `check_contraindication`/`check_black_box_warning` — given one
      medication, return curated free-text contraindication/black-box-
      warning language, or `None` when the port has no reference data
      for it.
    """

    @abstractmethod
    def check_patient_context_risks(
        self,
        medication: MedicationEntry,
        *,
        allergies: tuple[str, ...],
        medical_conditions: tuple[str, ...],
        pregnancy_status: PregnancyStatus | None,
        lactation_status: LactationStatus | None,
        patient_age: int | None,
    ) -> tuple[SafetyIssue, ...]: ...

    @abstractmethod
    def classify_pharmacologic_risk_flags(
        self, medication: MedicationEntry
    ) -> tuple[SafetyIssueCategory, ...]: ...

    @abstractmethod
    def check_contraindication(self, medication: MedicationEntry) -> str | None: ...

    @abstractmethod
    def check_black_box_warning(self, medication: MedicationEntry) -> str | None: ...


class DoseAdjustmentPort(ABC):
    """This task's own explicitly-named deterministic dose-adjustment
    seam — covering `SafetyIssueCategory.RENAL_DOSE_ADJUSTMENT`/
    `HEPATIC_DOSE_ADJUSTMENT`: given one medication and free-text renal/
    hepatic function descriptions (this task's own SUPPORTED INPUT
    section names both as free text, not structured lab values — see
    `domain/value_objects.py`'s own module docstring), deterministically
    suggests a dose-adjustment string from a curated renally-/
    hepatically-cleared medication reference table when the described
    function suggests impairment, or `None` when the port has no
    reference data for the medication or sees no impairment signal in
    the given text.
    """

    @abstractmethod
    def suggest_dose_adjustment(
        self,
        medication: MedicationEntry,
        *,
        renal_function: str | None,
        hepatic_function: str | None,
    ) -> str | None: ...


class InteractionEvidencePort(ABC):
    """This task's own explicitly-named deterministic evidence-grading
    seam — the safety-net half of drug-drug interaction detection (see
    `application/services/drug_interaction_service.DrugInteractionService`'s
    own docstring): given a drug pair, deterministically classifies its
    `EvidenceLevel` from the same curated reference table
    `DrugInteractionPort` draws on, used to verify/backfill an
    AI-reported interaction's evidence level rather than trusting an
    unverified AI claim outright. Returns `None` when the pair is not
    recognized (defer entirely to the AI's own reported evidence level,
    if any).
    """

    @abstractmethod
    def classify_evidence_level(self, drug_a: str, drug_b: str) -> EvidenceLevel | None: ...


class DrugSafetyAnalysisAuditLoggerPort(ABC):
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
