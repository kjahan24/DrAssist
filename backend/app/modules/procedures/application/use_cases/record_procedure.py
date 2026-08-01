"""`RecordVisitProcedure` — a procedure always references an existing
visit, and its `sequence_number` must be unique within that visit.

Unlike the Patient module's sub-resource use cases (which read the parent
`Patient` from a same-module repository), `VisitProcedure` references
`Visit` as a peer module — so it is resolved through its public facade
(`VisitQueryPort`), the same cross-module dependency pattern
`app.modules.diagnosis.application.use_cases.record_diagnosis.RecordVisitDiagnosis`
established for this codebase. `organization_id` is derived from the
visit's own summary (never accepted as a separate, independently
trustable input). A missing visit raises `PatientVisitNotFoundError`,
reused rather than wrapped, imported from `visit.public.exceptions` (a
re-export, not `visit.domain.exceptions` directly — see
`docs/backend-architecture/10_module_communication.md`, which forbids
depending on a peer module's `domain/`).

When `performed_by` is provided, it is resolved via `get_doctor_summary`
(not the cheaper `doctor_exists`) so its `organization_id` can be
compared against the visit's: a doctor belonging to a *different*
organization is treated identically to a missing one —
`DoctorNotFoundError`, never a distinct "wrong organization" error — the
same cross-tenant-as-not-found pattern `RecordVisitDiagnosis`/
`RecordVisitVitalSigns`/`RecordVisitChiefComplaint` already established.
"""

from app.modules.doctor.public.exceptions import DoctorNotFoundError
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.procedures.application.dto import (
    RecordVisitProcedureInput,
    RecordVisitProcedureOutput,
)
from app.modules.procedures.domain.entities import VisitProcedure
from app.modules.procedures.domain.exceptions import DuplicateSequenceNumberError
from app.modules.procedures.domain.repositories import VisitProcedureRepository
from app.modules.visit.public.exceptions import PatientVisitNotFoundError
from app.modules.visit.public.interfaces import VisitQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class RecordVisitProcedure(UseCase[RecordVisitProcedureInput, RecordVisitProcedureOutput]):
    def __init__(
        self,
        *,
        procedure_repository: VisitProcedureRepository,
        visit_query_port: VisitQueryPort,
        doctor_query_port: DoctorQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._procedures = procedure_repository
        self._visits = visit_query_port
        self._doctors = doctor_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: RecordVisitProcedureInput) -> RecordVisitProcedureOutput:
        visit_summary = await self._visits.get_visit_summary(input_dto.visit_id)
        if visit_summary is None:
            raise PatientVisitNotFoundError(input_dto.visit_id)

        if input_dto.performed_by is not None:
            doctor_summary = await self._doctors.get_doctor_summary(input_dto.performed_by)
            if (
                doctor_summary is None
                or doctor_summary.organization_id != visit_summary.organization_id
            ):
                raise DoctorNotFoundError(input_dto.performed_by)

        existing = await self._procedures.get_by_visit_and_sequence(
            visit_id=input_dto.visit_id, sequence_number=input_dto.sequence_number
        )
        if existing is not None:
            raise DuplicateSequenceNumberError(input_dto.visit_id, input_dto.sequence_number)

        procedure = VisitProcedure.create(
            organization_id=visit_summary.organization_id,
            visit_id=input_dto.visit_id,
            sequence_number=input_dto.sequence_number,
            procedure_name=input_dto.procedure_name,
            procedure_code=input_dto.procedure_code,
            procedure_category=input_dto.procedure_category,
            procedure_status=input_dto.procedure_status,
            performed_by=input_dto.performed_by,
            performed_at=input_dto.performed_at,
            notes=input_dto.notes,
        )
        await self._procedures.add(procedure)
        self._uow.collect_events(procedure.pull_events())
        await self._uow.commit()

        return RecordVisitProcedureOutput(
            procedure_id=procedure.id,
            organization_id=procedure.organization_id,
            visit_id=procedure.visit_id,
            sequence_number=procedure.sequence_number,
            procedure_status=procedure.procedure_status,
        )
