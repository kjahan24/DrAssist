"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`ScheduleVisit` needs both the Patient and Doctor modules' public
facades; both are built via their own `build_patient_facade`/
`build_doctor_facade` composition roots (bound to the same `session`)
rather than duplicating facade construction here — the same pattern
`app.modules.patient.api.dependencies` established.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.doctor.container import build_doctor_facade
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.patient.container import build_patient_facade
from app.modules.patient.public.interfaces import PatientQueryPort
from app.modules.visit.application.services.patient_visit_query_service import (
    PatientVisitQueryService,
)
from app.modules.visit.application.use_cases.schedule_visit import ScheduleVisit
from app.modules.visit.domain.repositories import PatientVisitRepository
from app.modules.visit.infrastructure.repositories import SqlAlchemyPatientVisitRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_patient_visit_repository(session: DbSession) -> PatientVisitRepository:
    return SqlAlchemyPatientVisitRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_patient_query_port(session: DbSession) -> PatientQueryPort:
    return build_patient_facade(session)


def get_doctor_query_port(session: DbSession) -> DoctorQueryPort:
    return build_doctor_facade(session)


PatientVisitRepo = Annotated[PatientVisitRepository, Depends(get_patient_visit_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
PatientPort = Annotated[PatientQueryPort, Depends(get_patient_query_port)]
DoctorPort = Annotated[DoctorQueryPort, Depends(get_doctor_query_port)]


def get_patient_visit_query_service(
    patient_visit_repository: PatientVisitRepo,
) -> PatientVisitQueryService:
    return PatientVisitQueryService(patient_visit_repository=patient_visit_repository)


def get_schedule_visit_use_case(
    patient_visit_repository: PatientVisitRepo,
    patient_query_port: PatientPort,
    doctor_query_port: DoctorPort,
    unit_of_work: Uow,
) -> ScheduleVisit:
    return ScheduleVisit(
        patient_visit_repository=patient_visit_repository,
        patient_query_port=patient_query_port,
        doctor_query_port=doctor_query_port,
        unit_of_work=unit_of_work,
    )
