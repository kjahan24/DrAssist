"""Application-layer ports for the AI Prescription Assistance module, per
this task's explicit "Define PrescriptionGeneratorPort,
PrescriptionPromptBuilderPort, MedicationKnowledgePort,
DrugInteractionPort" requirement (extended here with the template-
selector/parser/validator/audit/cost ports the rest of the task's
pipeline needs — the same "named ports plus the operationally-necessary
rest" shape `app.modules.icd10_ai.application.ports` establishes for its
own module, whose own docstring documents the identical reasoning).

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
from app.modules.prescription_ai.domain.enums import PrescribingSetting, PrescriptionOutputFormat
from app.modules.prescription_ai.domain.value_objects import (
    GenerationSession,
    MedicationSafetyFinding,
    PrescriptionContextInput,
    PrescriptionStreamChunk,
    PrescriptionSuggestionSet,
    PrescriptionTemplateSet,
)


class PrescriptionTemplateSelectorPort(ABC):
    @abstractmethod
    def select(self, prescribing_setting: PrescribingSetting) -> PrescriptionTemplateSet: ...


class PrescriptionPromptBuilderPort(ABC):
    @abstractmethod
    async def build_messages(
        self, context: PrescriptionContextInput, template_set: PrescriptionTemplateSet
    ) -> list[AIMessage]: ...


class PrescriptionGeneratorPort(ABC):
    """The seam `infrastructure/generation/prescription_generator.py`
    implements over AI Foundation's `AIGatewayPort` — use cases depend on
    this port, never on AI Foundation directly.

    `generate` returns the **raw** AI reply text, not yet a parsed
    `PrescriptionSuggestionSet` — parsing is
    `PrescriptionSuggestionParserPort`'s own, separately-testable
    concern, the same split
    `app.modules.icd10_ai.application.ports.ICD10GeneratorPort` documents
    for itself.
    """

    @abstractmethod
    async def generate(
        self, context: PrescriptionContextInput
    ) -> tuple[str, GenerationSession]: ...

    @abstractmethod
    def stream_generate(
        self, context: PrescriptionContextInput
    ) -> AsyncIterator[PrescriptionStreamChunk]: ...


class PrescriptionSuggestionParserPort(ABC):
    @abstractmethod
    def parse(
        self, raw_text: str, *, output_format: PrescriptionOutputFormat
    ) -> PrescriptionSuggestionSet:
        """Raises `InvalidPrescriptionResponseFormatError` (domain) when
        `raw_text` cannot be parsed into a `PrescriptionSuggestionSet`."""
        ...


class PrescriptionSuggestionValidatorPort(ABC):
    @abstractmethod
    def validate(self, suggestion_set: PrescriptionSuggestionSet) -> None:
        """Raises `EmptyPrescriptionResponseError`/
        `InvalidMedicationStructureError`/`DuplicateMedicationError`/
        `MissingMedicationDosageError`/`MissingMedicationFrequencyError`/
        `MissingMedicationDurationError`/`HallucinatedMedicationError`
        (domain) when invalid; returns `None` when valid."""
        ...


class MedicationKnowledgePort(ABC):
    """This module's own small medication knowledge surface — a real
    production system would call a licensed, regularly-updated drug
    formulary/knowledge-base API; this port is the seam that swaps in
    for one without the application layer (the deterministic safety
    analysis service) ever depending on how that lookup is actually
    implemented. Mirrors the "structural/soft signal, not a hard
    validation gate" split `app.modules.icd10_ai.application.ports
    .ICD10KnowledgePort` documents for its own two methods — but unlike
    that port's `is_valid_format` (a complete structural regex),
    medication names have no rigid shape to validate against, so neither
    of this port's methods is a hard validation gate; "invalid medication
    structure" in this module's own VALIDATION section instead means a
    structurally incomplete record (a blank `generic_name`), checked
    directly by `PrescriptionSuggestionValidatorPort` with no port
    dependency at all.
    """

    @abstractmethod
    def is_known_medication(self, generic_name: str) -> bool: ...

    @abstractmethod
    def lookup_therapeutic_class(self, generic_name: str) -> str | None: ...


class DrugInteractionPort(ABC):
    """The deterministic half of this task's own "MEDICATION SAFETY"
    requirement — a curated reference-table safety net independent of
    whatever the AI itself claims in its response, checked by
    `application/services/medication_safety_analysis_service.py` and
    merged with the AI's own self-reported findings by
    `GeneratePrescriptionSuggestionUseCase`. See
    `MedicationSafetyFinding`'s own docstring for the full reasoning on
    why both sources exist."""

    @abstractmethod
    def check_interactions(
        self, generic_names: tuple[str, ...]
    ) -> tuple[MedicationSafetyFinding, ...]: ...

    @abstractmethod
    def check_allergy_conflicts(
        self, generic_names: tuple[str, ...], allergies: tuple[str, ...]
    ) -> tuple[MedicationSafetyFinding, ...]: ...


class PrescriptionAuditLoggerPort(ABC):
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
    reasoning `app.modules.icd10_ai.application.ports.CostEstimatorPort`
    documents for itself."""

    def estimate(
        self, *, provider: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float: ...
