"""Read-only queries against `PatientVisit`.

Backs the module's public `VisitQueryPort` — the one implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

`list_visits_for_patient` and `VisitSummaryDTO`'s extra fields were added
by the REST APIs task — the repository already had `list_by_patient`
(needed for "List" per this task's own REST conventions), just not
exposed through the query service yet, and `api/schemas.py`'s own
`PatientVisitResponse` (built in this module's original task, before
endpoints existed) already expected the fuller shape than
`VisitSummaryDTO` carried — see
`app.modules.diagnosis.application.services.diagnosis_query_service`'s
own docstring for the identical reasoning applied elsewhere in this
task. Purely additive: every existing consumer of `VisitQueryPort`
(Appointment, Diagnosis, Procedures, ...) only reads the fields it
already knew about.
"""

from uuid import UUID

from app.modules.visit.application.dto import VisitSummaryDTO
from app.modules.visit.domain.entities import PatientVisit
from app.modules.visit.domain.enums import VisitStatus
from app.modules.visit.domain.repositories import PatientVisitRepository

_NON_TERMINAL_STATUSES = frozenset(
    {VisitStatus.SCHEDULED, VisitStatus.CHECKED_IN, VisitStatus.IN_PROGRESS}
)


class PatientVisitQueryService:
    def __init__(self, *, patient_visit_repository: PatientVisitRepository) -> None:
        self._visits = patient_visit_repository

    async def visit_exists(self, visit_id: UUID) -> bool:
        return await self._visits.get_by_id(visit_id) is not None

    async def is_active(self, visit_id: UUID) -> bool:
        """ "Active" means not yet in a terminal state (`Completed`,
        `Cancelled`, `No Show`) — i.e. still scheduled, checked in, or in
        progress."""
        visit = await self._visits.get_by_id(visit_id)
        return visit is not None and visit.visit_status in _NON_TERMINAL_STATUSES

    async def get_visit_summary(self, visit_id: UUID) -> VisitSummaryDTO | None:
        visit = await self._visits.get_by_id(visit_id)
        return _to_summary(visit) if visit is not None else None

    async def list_visits_for_patient(self, patient_id: UUID) -> list[VisitSummaryDTO]:
        visits = await self._visits.list_by_patient(patient_id)
        return [_to_summary(visit) for visit in visits]


def _to_summary(visit: PatientVisit) -> VisitSummaryDTO:
    return VisitSummaryDTO(
        visit_id=visit.id,
        organization_id=visit.organization_id,
        patient_id=visit.patient_id,
        doctor_id=visit.doctor_id,
        visit_number=visit.visit_number,
        visit_status=visit.visit_status,
        visit_type=visit.visit_type,
        appointment_id=visit.appointment_id,
        priority=visit.priority,
        visit_date=visit.visit_date,
        check_in_time=visit.check_in_time,
        consultation_start_time=visit.consultation_start_time,
        consultation_end_time=visit.consultation_end_time,
        check_out_time=visit.check_out_time,
        chief_complaint_summary=visit.chief_complaint_summary,
        reason_for_visit=visit.reason_for_visit,
        room_number=visit.room_number,
        follow_up_required=visit.follow_up_required,
        follow_up_date=visit.follow_up_date,
        notes=visit.notes,
    )
