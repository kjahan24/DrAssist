"""Read-only queries against `VisitProcedure`.

Backs the module's public `ProcedureQueryPort` — the one implementation,
per `docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).
"""

from uuid import UUID

from app.modules.procedures.application.dto import ProcedureSummaryDTO
from app.modules.procedures.domain.repositories import VisitProcedureRepository


class VisitProcedureQueryService:
    def __init__(self, *, procedure_repository: VisitProcedureRepository) -> None:
        self._procedures = procedure_repository

    async def procedure_exists(self, procedure_id: UUID) -> bool:
        return await self._procedures.get_by_id(procedure_id) is not None

    async def list_procedures_for_visit(self, visit_id: UUID) -> list[ProcedureSummaryDTO]:
        procedures = await self._procedures.list_by_visit(visit_id)
        return [
            ProcedureSummaryDTO(
                procedure_id=procedure.id,
                organization_id=procedure.organization_id,
                visit_id=procedure.visit_id,
                sequence_number=procedure.sequence_number,
                procedure_name=procedure.procedure_name,
                procedure_status=procedure.procedure_status,
            )
            for procedure in procedures
        ]
