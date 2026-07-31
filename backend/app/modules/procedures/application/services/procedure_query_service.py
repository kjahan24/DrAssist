"""Read-only queries against `VisitProcedure`.

Backs the module's public `ProcedureQueryPort` — the one implementation,
per `docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

`get_procedure_summary`/`ProcedureSummaryDTO`'s extra fields were added
by the REST APIs task — see `app.modules.diagnosis.application.services
.diagnosis_query_service`'s own docstring for the identical reasoning.
"""

from uuid import UUID

from app.modules.procedures.application.dto import ProcedureSummaryDTO
from app.modules.procedures.domain.entities import VisitProcedure
from app.modules.procedures.domain.repositories import VisitProcedureRepository


class VisitProcedureQueryService:
    def __init__(self, *, procedure_repository: VisitProcedureRepository) -> None:
        self._procedures = procedure_repository

    async def procedure_exists(self, procedure_id: UUID) -> bool:
        return await self._procedures.get_by_id(procedure_id) is not None

    async def get_procedure_summary(self, procedure_id: UUID) -> ProcedureSummaryDTO | None:
        procedure = await self._procedures.get_by_id(procedure_id)
        return _to_summary(procedure) if procedure is not None else None

    async def list_procedures_for_visit(self, visit_id: UUID) -> list[ProcedureSummaryDTO]:
        procedures = await self._procedures.list_by_visit(visit_id)
        return [_to_summary(procedure) for procedure in procedures]


def _to_summary(procedure: VisitProcedure) -> ProcedureSummaryDTO:
    return ProcedureSummaryDTO(
        procedure_id=procedure.id,
        organization_id=procedure.organization_id,
        visit_id=procedure.visit_id,
        sequence_number=procedure.sequence_number,
        procedure_name=procedure.procedure_name,
        procedure_status=procedure.procedure_status,
        procedure_code=procedure.procedure_code,
        procedure_category=procedure.procedure_category,
        performed_by=procedure.performed_by,
        performed_at=procedure.performed_at,
        notes=procedure.notes,
    )
