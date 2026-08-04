"""Unit tests for `RankICD10SuggestionsUseCase`."""

from app.modules.icd10_ai.application.services.icd10_ranking_service import ICD10RankingService
from app.modules.icd10_ai.application.use_cases.rank_icd10_suggestions import (
    RankICD10SuggestionsUseCase,
)
from app.modules.icd10_ai.domain.enums import DiagnosisFlag
from tests.unit.modules.icd10_ai.application.fakes import (
    FakeICD10KnowledgePort,
    make_suggestion,
    make_suggestion_set,
)


class TestRankICD10SuggestionsUseCase:
    async def test_delegates_to_the_ranking_service(self) -> None:
        use_case = RankICD10SuggestionsUseCase(
            ranking_service=ICD10RankingService(knowledge=FakeICD10KnowledgePort())
        )
        suggestion_set = make_suggestion_set(
            suggestions=(
                make_suggestion(icd10_code="A00", flag=DiagnosisFlag.SECONDARY),
                make_suggestion(icd10_code="B00", flag=DiagnosisFlag.PRIMARY),
            )
        )

        result = await use_case.execute(suggestion_set)

        assert result.suggestions[0].flag is DiagnosisFlag.PRIMARY
