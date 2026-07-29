"""`ProcedureFacade` — the one concrete implementation of
`ProcedureQueryPort`. Constructed per-request by
`app.modules.procedures.container.build_procedure_facade`, bound to that
request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.procedures.application.services.procedure_query_service import (
    VisitProcedureQueryService,
)
from app.modules.procedures.public.dto import ProcedureSummaryDTO
from app.modules.procedures.public.interfaces import ProcedureQueryPort


class ProcedureFacade(ProcedureQueryPort):
    def __init__(self, *, query_service: VisitProcedureQueryService) -> None:
        self._query_service = query_service

    async def procedure_exists(self, procedure_id: UUID) -> bool:
        return await self._query_service.procedure_exists(procedure_id)

    async def list_procedures_for_visit(self, visit_id: UUID) -> list[ProcedureSummaryDTO]:
        return await self._query_service.list_procedures_for_visit(visit_id)
