"""`RankICD10SuggestionsUseCase` — a standalone entry point onto
`ICD10RankingService` for a caller that already has an assembled
`ICD10SuggestionSet` (e.g. merged across multiple generations or
supplied by a future consumer module) and wants it (re-)ranked without a
further AI call. `GenerateICD10SuggestionsUseCase` uses the same
`ICD10RankingService` instance directly as its own last pipeline step —
see that use case's own module docstring."""

from app.modules.icd10_ai.application.services.icd10_ranking_service import ICD10RankingService
from app.modules.icd10_ai.domain.value_objects import ICD10SuggestionSet
from app.shared.application.use_case import UseCase


class RankICD10SuggestionsUseCase(UseCase[ICD10SuggestionSet, ICD10SuggestionSet]):
    def __init__(self, *, ranking_service: ICD10RankingService) -> None:
        self._ranking_service = ranking_service

    async def execute(self, input_dto: ICD10SuggestionSet) -> ICD10SuggestionSet:
        return self._ranking_service.rank(input_dto)
