"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`RecordVisitChiefComplaint` needs both the Visit and Doctor modules'
public facades; both are built via their own `build_visit_facade`/
`build_doctor_facade` composition roots (bound to the same `session`)
rather than duplicating facade construction here — the same pattern
`app.modules.vital_signs.api.dependencies` established.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.chief_complaints.application.services.chief_complaint_query_service import (
    VisitChiefComplaintQueryService,
)
from app.modules.chief_complaints.application.use_cases.record_chief_complaint import (
    RecordVisitChiefComplaint,
)
from app.modules.chief_complaints.domain.repositories import VisitChiefComplaintRepository
from app.modules.chief_complaints.infrastructure.repositories import (
    SqlAlchemyVisitChiefComplaintRepository,
)
from app.modules.doctor.container import build_doctor_facade
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.visit.container import build_visit_facade
from app.modules.visit.public.interfaces import VisitQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_chief_complaint_repository(session: DbSession) -> VisitChiefComplaintRepository:
    return SqlAlchemyVisitChiefComplaintRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_visit_query_port(session: DbSession) -> VisitQueryPort:
    return build_visit_facade(session)


def get_doctor_query_port(session: DbSession) -> DoctorQueryPort:
    return build_doctor_facade(session)


ChiefComplaintRepo = Annotated[
    VisitChiefComplaintRepository, Depends(get_chief_complaint_repository)
]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
VisitPort = Annotated[VisitQueryPort, Depends(get_visit_query_port)]
DoctorPort = Annotated[DoctorQueryPort, Depends(get_doctor_query_port)]


def get_chief_complaint_query_service(
    chief_complaint_repository: ChiefComplaintRepo,
) -> VisitChiefComplaintQueryService:
    return VisitChiefComplaintQueryService(chief_complaint_repository=chief_complaint_repository)


def get_record_chief_complaint_use_case(
    chief_complaint_repository: ChiefComplaintRepo,
    visit_query_port: VisitPort,
    doctor_query_port: DoctorPort,
    unit_of_work: Uow,
) -> RecordVisitChiefComplaint:
    return RecordVisitChiefComplaint(
        chief_complaint_repository=chief_complaint_repository,
        visit_query_port=visit_query_port,
        doctor_query_port=doctor_query_port,
        unit_of_work=unit_of_work,
    )
