"""`RankDifferentialDiagnosisUseCase` — a standalone entry point onto
`DifferentialDiagnosisRankingService` for a caller that already has an
assembled `DifferentialDiagnosisResult` (e.g. merged across multiple
generations or supplied by a future consumer module) and wants it
(re-)ranked without a further AI call. `GenerateDifferentialDiagnosisUseCase`
uses the same `DifferentialDiagnosisRankingService` instance directly as
its own last pipeline step — see that use case's own module docstring.
"""

from app.modules.differential_diagnosis_ai.application.services.differential_diagnosis_ranking_service import (  # noqa: E501
    DifferentialDiagnosisRankingService,
)
from app.modules.differential_diagnosis_ai.domain.value_objects import DifferentialDiagnosisResult
from app.shared.application.use_case import UseCase


class RankDifferentialDiagnosisUseCase(
    UseCase[DifferentialDiagnosisResult, DifferentialDiagnosisResult]
):
    def __init__(self, *, ranking_service: DifferentialDiagnosisRankingService) -> None:
        self._ranking_service = ranking_service

    async def execute(self, input_dto: DifferentialDiagnosisResult) -> DifferentialDiagnosisResult:
        return self._ranking_service.rank(input_dto)
