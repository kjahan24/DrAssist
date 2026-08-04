"""Unit tests for `RankDifferentialDiagnosisUseCase`."""

from app.modules.differential_diagnosis_ai.application.services.differential_diagnosis_ranking_service import (  # noqa: E501
    DifferentialDiagnosisRankingService,
)
from app.modules.differential_diagnosis_ai.application.use_cases.rank_differential_diagnosis import (  # noqa: E501
    RankDifferentialDiagnosisUseCase,
)
from tests.unit.modules.differential_diagnosis_ai.application.fakes import (
    make_candidate,
    make_result,
)


class TestRankDifferentialDiagnosisUseCase:
    async def test_delegates_to_the_ranking_service(self) -> None:
        use_case = RankDifferentialDiagnosisUseCase(
            ranking_service=DifferentialDiagnosisRankingService()
        )
        result = make_result(
            candidates=(
                make_candidate(disease_name="Bronchitis", confidence_score=0.2),
                make_candidate(disease_name="Pneumonia", confidence_score=0.9),
            )
        )

        ranked = await use_case.execute(result)

        assert ranked.candidates[0].disease_name == "Pneumonia"
