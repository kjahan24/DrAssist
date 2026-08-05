"""Application-layer ports for the AI Patient Education & Discharge
Instructions module, per this task's explicit "Create ports:
PatientEducationPort, DischargeInstructionPort,
LifestyleRecommendationPort" requirement — extended here with the
generation/prompt/parsing/validation/audit/cost/template-selection
ports the rest of the task's pipeline needs, the same "named ports plus
the operationally-necessary rest" shape every prior AI module's own
`application/ports.py` establishes for itself
(`app.modules.risk_stratification_ai.application.ports` is the most
directly analogous precedent, itself naming three explicit ports plus a
prefixed operational set). This task names no "XxxInterpreterPort"/
"XxxPromptBuilderPort" pair of its own, so the operationally-necessary
generation/prompt-building ports are named with a
`PatientEducationAnalysis` prefix — deliberately distinct from the
three explicitly-named ports below.

Depends on AI Foundation's `public/` surface only (`AIMessage`), never
its `.application`/`.infrastructure` — rule: "Reuse the existing AI
Foundation... wherever possible" is satisfied by calling through its
public `AIGatewayPort`, never a provider SDK directly.

This module's genuine reuse of `app.modules.medical_reasoning_ai` is
*not* modeled as one of these ports — `application/use_cases
/generate_patient_education.py` depends directly on that peer module's
own public port, `MedicalReasoningAIPort`
(`app.modules.medical_reasoning_ai.public.interfaces`), the same way
every prior interpretation-AI module's own use case already does for
itself. See `container.py`'s own module docstring for the full
reasoning, including why no other peer AI module's public port
(`PrescriptionAIPort`/`DrugInteractionAIPort`/
`RiskStratificationAIPort`/`LabInterpreterPort`/
`RadiologyInterpreterPort`/`PathologyInterpreterPort`/
`DifferentialDiagnosisAIPort`) is called into directly — this module
accepts their already-generated summaries as plain `str | None` input
fields instead (see `domain/value_objects.py`'s own module docstring).
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from app.modules.ai.public.dto import AIMessage
from app.modules.patient_education_ai.domain.enums import (
    PatientEducationOutputFormat,
    PatientEducationSetting,
)
from app.modules.patient_education_ai.domain.value_objects import (
    GenerationSession,
    PatientEducationInput,
    PatientEducationResult,
    PatientEducationStreamChunk,
    PatientEducationTemplateSet,
)


class PatientEducationAnalysisTemplateSelectorPort(ABC):
    @abstractmethod
    def select(self, education_setting: PatientEducationSetting) -> PatientEducationTemplateSet: ...


class PatientEducationAnalysisPromptBuilderPort(ABC):
    @abstractmethod
    async def build_messages(
        self,
        input_dto: PatientEducationInput,
        template_set: PatientEducationTemplateSet,
    ) -> list[AIMessage]: ...


class PatientEducationAnalysisGeneratorPort(ABC):
    """The seam `infrastructure/generation
    /patient_education_generator.py` implements over AI Foundation's
    `AIGatewayPort` — the use case depends on this port, never on AI
    Foundation directly.

    `generate` returns the **raw** AI reply text, not yet a parsed
    `PatientEducationResult` — parsing is
    `PatientEducationAnalysisParserPort`'s own, separately-testable
    concern.
    """

    @abstractmethod
    async def generate(self, input_dto: PatientEducationInput) -> tuple[str, GenerationSession]: ...

    @abstractmethod
    def stream_generate(
        self, input_dto: PatientEducationInput
    ) -> AsyncIterator[PatientEducationStreamChunk]: ...


class PatientEducationAnalysisParserPort(ABC):
    @abstractmethod
    def parse(
        self, raw_text: str, *, output_format: PatientEducationOutputFormat
    ) -> PatientEducationResult:
        """Raises `InvalidPatientEducationResponseFormatError` (domain)
        when `raw_text` cannot be parsed into a
        `PatientEducationResult`."""
        ...


class PatientEducationAnalysisValidatorPort(ABC):
    @abstractmethod
    def validate(self, result: PatientEducationResult, input_dto: PatientEducationInput) -> None:
        """Raises `HallucinatedRecommendationError`/`UnsafeInstructionError`/
        `InvalidPatientEducationConfidenceValueError` (domain) when
        invalid; returns `None` when valid."""
        ...


class PatientEducationPort(ABC):
    """This task's own explicitly-named deterministic diagnosis-
    education seam — a curated reference table of patient-friendly
    diagnosis explanations and their standard warning signs/emergency
    symptoms, the same "each module defines its own local, necessarily-
    incomplete copy" precedent every prior AI module's own knowledge-
    base port establishes for itself.

    Given a diagnosis name, deterministically returns curated
    patient-friendly content when the diagnosis is recognized, or
    `None`/an empty tuple when it is not — never a fabricated
    explanation for a diagnosis this port does not actually have
    reference data for.
    """

    @abstractmethod
    def explain_diagnosis(self, diagnosis: str) -> str | None: ...

    @abstractmethod
    def identify_warning_signs(self, diagnosis: str) -> tuple[str, ...]: ...

    @abstractmethod
    def identify_emergency_symptoms(self, diagnosis: str) -> tuple[str, ...]: ...


class DischargeInstructionPort(ABC):
    """This task's own explicitly-named deterministic discharge seam —
    covering medication-taking/adherence instructions, home/wound care
    instructions, and the discharge checklist: a curated reference
    table keyed by medication name and by diagnosis keyword, the same
    "necessarily incomplete curated table" precedent every prior AI
    module's own knowledge-base port establishes for itself.
    """

    @abstractmethod
    def instruct_medication(self, medication: str) -> str | None: ...

    @abstractmethod
    def generate_home_care_instructions(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]: ...

    @abstractmethod
    def generate_discharge_checklist(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]: ...


class LifestyleRecommendationPort(ABC):
    """This task's own explicitly-named deterministic lifestyle seam —
    covering lifestyle, diet, exercise, and preventive-care/vaccination
    recommendations: a curated reference table keyed by diagnosis
    keyword (and, for preventive care, patient age), the same
    "necessarily incomplete curated table" precedent every prior AI
    module's own knowledge-base port establishes for itself.
    """

    @abstractmethod
    def recommend_lifestyle(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]: ...

    @abstractmethod
    def recommend_diet(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]: ...

    @abstractmethod
    def recommend_exercise(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]: ...

    @abstractmethod
    def recommend_preventive_care(
        self, diagnoses: tuple[str, ...], patient_age: int | None
    ) -> tuple[str, ...]: ...


class PatientEducationAnalysisAuditLoggerPort(ABC):
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
