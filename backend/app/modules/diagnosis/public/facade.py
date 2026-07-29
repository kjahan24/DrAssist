"""`DiagnosisFacade` — the one concrete implementation of
`DiagnosisQueryPort`. Constructed per-request by
`app.modules.diagnosis.container.build_diagnosis_facade`, bound to that
request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.diagnosis.application.services.diagnosis_query_service import (
    VisitDiagnosisQueryService,
)
from app.modules.diagnosis.public.dto import DiagnosisSummaryDTO
from app.modules.diagnosis.public.interfaces import DiagnosisQueryPort


class DiagnosisFacade(DiagnosisQueryPort):
    def __init__(self, *, query_service: VisitDiagnosisQueryService) -> None:
        self._query_service = query_service

    async def diagnosis_exists(self, diagnosis_id: UUID) -> bool:
        return await self._query_service.diagnosis_exists(diagnosis_id)

    async def list_diagnoses_for_visit(self, visit_id: UUID) -> list[DiagnosisSummaryDTO]:
        return await self._query_service.list_diagnoses_for_visit(visit_id)
