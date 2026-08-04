"""The AI Prescription Assistance module's public port — the only
contract another module may depend on
(`docs/backend-architecture/03_module_architecture.md`,
`10_module_communication.md`).

Never import from `app.modules.prescription_ai.domain`, `.application`
(beyond this package's own re-exports in `public/dto.py`), or
`.infrastructure` from outside this module. The pre-existing
`app.modules.prescriptions` module (structured, persisted prescription
records — a completed backend module, not modified by this task) is the
expected future consumer of this one's `generate_suggestion`: it lets a
physician review/edit an AI-drafted suggestion before persisting it as a
real `PrescriptionStatus.DRAFT`/`FINAL` record — this module itself
never issues or saves anything, per this task's own "It NEVER issues a
prescription. It NEVER saves prescriptions. It NEVER replaces physician
judgment. Every output is a draft requiring physician review" scope.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.modules.prescription_ai.public.dto import (
    GeneratedPrescriptionSuggestions,
    MedicationSafetyFinding,
    PrescriptionContextInput,
    PrescriptionContextValidationResultDTO,
    PrescriptionOutputFormat,
    PrescriptionStreamChunk,
    PrescriptionSuggestionSet,
)


class PrescriptionAIPort(ABC):
    @abstractmethod
    async def generate_suggestion(
        self, context: PrescriptionContextInput
    ) -> GeneratedPrescriptionSuggestions: ...

    @abstractmethod
    def stream_generate_suggestion(
        self, context: PrescriptionContextInput
    ) -> AsyncIterator[PrescriptionStreamChunk]: ...

    @abstractmethod
    async def analyze_medication_safety(
        self,
        suggestion_set: PrescriptionSuggestionSet,
        *,
        existing_medications: tuple[str, ...] = (),
        allergies: tuple[str, ...] = (),
    ) -> tuple[MedicationSafetyFinding, ...]: ...

    @abstractmethod
    async def render_suggestions(
        self, suggestion_set: PrescriptionSuggestionSet, *, target_format: PrescriptionOutputFormat
    ) -> str: ...

    @abstractmethod
    async def validate_context(
        self, context: PrescriptionContextInput
    ) -> PrescriptionContextValidationResultDTO: ...
