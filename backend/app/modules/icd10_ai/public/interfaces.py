"""The AI ICD-10 Coding module's public port — the only contract another
module may depend on (`docs/backend-architecture/03_module_architecture.md`,
`10_module_communication.md`).

Never import from `app.modules.icd10_ai.domain`, `.application` (beyond
this package's own re-exports in `public/dto.py`), or `.infrastructure`
from outside this module. The pre-existing `app.modules.icd10_coding`
module (structured, persisted ICD-10 coding records — a completed
backend module, not modified by this task) is the expected future
consumer of this one's `generate_suggestions`/`rank_suggestions`: it
lets a clinician review/edit an AI-drafted suggestion before persisting
it as a `CodingSource.AI`/`CodingSource.HYBRID` record — this module
itself never saves anything, per this task's own "It ONLY generates
coding suggestions. It NEVER stores diagnoses. It NEVER modifies patient
records" scope.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.modules.icd10_ai.public.dto import (
    ClinicalContextValidationResultDTO,
    GeneratedICD10Suggestions,
    ICD10CodingInput,
    ICD10OutputFormat,
    ICD10StreamChunk,
    ICD10SuggestionSet,
)


class ICD10AIPort(ABC):
    @abstractmethod
    async def generate_suggestions(
        self, coding_input: ICD10CodingInput
    ) -> GeneratedICD10Suggestions: ...

    @abstractmethod
    def stream_generate_suggestions(
        self, coding_input: ICD10CodingInput
    ) -> AsyncIterator[ICD10StreamChunk]: ...

    @abstractmethod
    async def rank_suggestions(self, suggestion_set: ICD10SuggestionSet) -> ICD10SuggestionSet: ...

    @abstractmethod
    async def render_suggestions(
        self, suggestion_set: ICD10SuggestionSet, *, target_format: ICD10OutputFormat
    ) -> str: ...

    @abstractmethod
    async def validate_context(
        self, coding_input: ICD10CodingInput
    ) -> ClinicalContextValidationResultDTO: ...
