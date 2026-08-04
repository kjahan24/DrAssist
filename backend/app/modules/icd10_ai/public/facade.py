"""`ICD10AIFacade` — the one concrete implementation of `ICD10AIPort`.
Constructed by `app.modules.icd10_ai.container.get_icd10_ai_facade`.

`render_suggestions` delegates directly to `ICD10SuggestionRenderer`
(not a use case) — see that service's own module docstring for why: this
task names exactly three use cases, none of them a rendering one.
"""

from collections.abc import AsyncIterator

from app.modules.icd10_ai.application.ports import ICD10GeneratorPort
from app.modules.icd10_ai.application.services.icd10_suggestion_renderer import (
    ICD10SuggestionRenderer,
)
from app.modules.icd10_ai.application.use_cases.generate_icd10_suggestions import (
    GenerateICD10SuggestionsUseCase,
)
from app.modules.icd10_ai.application.use_cases.rank_icd10_suggestions import (
    RankICD10SuggestionsUseCase,
)
from app.modules.icd10_ai.application.use_cases.validate_clinical_context import (
    ValidateClinicalContextUseCase,
)
from app.modules.icd10_ai.public.dto import (
    ClinicalContextValidationResultDTO,
    GeneratedICD10Suggestions,
    ICD10CodingInput,
    ICD10OutputFormat,
    ICD10StreamChunk,
    ICD10SuggestionSet,
)
from app.modules.icd10_ai.public.interfaces import ICD10AIPort


class ICD10AIFacade(ICD10AIPort):
    def __init__(
        self,
        *,
        generate_use_case: GenerateICD10SuggestionsUseCase,
        validate_use_case: ValidateClinicalContextUseCase,
        rank_use_case: RankICD10SuggestionsUseCase,
        renderer: ICD10SuggestionRenderer,
        generator: ICD10GeneratorPort,
    ) -> None:
        self._generate_use_case = generate_use_case
        self._validate_use_case = validate_use_case
        self._rank_use_case = rank_use_case
        self._renderer = renderer
        self._generator = generator

    async def generate_suggestions(
        self, coding_input: ICD10CodingInput
    ) -> GeneratedICD10Suggestions:
        return await self._generate_use_case.execute(coding_input)

    def stream_generate_suggestions(
        self, coding_input: ICD10CodingInput
    ) -> AsyncIterator[ICD10StreamChunk]:
        return self._generator.stream_generate(coding_input)

    async def rank_suggestions(self, suggestion_set: ICD10SuggestionSet) -> ICD10SuggestionSet:
        return await self._rank_use_case.execute(suggestion_set)

    async def render_suggestions(
        self, suggestion_set: ICD10SuggestionSet, *, target_format: ICD10OutputFormat
    ) -> str:
        return self._renderer.render(suggestion_set, target_format)

    async def validate_context(
        self, coding_input: ICD10CodingInput
    ) -> ClinicalContextValidationResultDTO:
        return await self._validate_use_case.execute(coding_input)
