"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`RecordVisitVitalSigns` needs both the Visit and Doctor modules' public
facades; both are built via their own `build_visit_facade`/
`build_doctor_facade` composition roots (bound to the same `session`)
rather than duplicating facade construction here — the same pattern
`app.modules.visit.api.dependencies` established.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.doctor.container import build_doctor_facade
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.visit.container import build_visit_facade
from app.modules.visit.public.interfaces import VisitQueryPort
from app.modules.vital_signs.application.services.vital_signs_query_service import (
    VisitVitalSignsQueryService,
)
from app.modules.vital_signs.application.use_cases.record_vital_signs import (
    RecordVisitVitalSigns,
)
from app.modules.vital_signs.domain.repositories import VisitVitalSignsRepository
from app.modules.vital_signs.infrastructure.repositories import (
    SqlAlchemyVisitVitalSignsRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_vital_signs_repository(session: DbSession) -> VisitVitalSignsRepository:
    return SqlAlchemyVisitVitalSignsRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_visit_query_port(session: DbSession) -> VisitQueryPort:
    return build_visit_facade(session)


def get_doctor_query_port(session: DbSession) -> DoctorQueryPort:
    return build_doctor_facade(session)


VitalSignsRepo = Annotated[VisitVitalSignsRepository, Depends(get_vital_signs_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
VisitPort = Annotated[VisitQueryPort, Depends(get_visit_query_port)]
DoctorPort = Annotated[DoctorQueryPort, Depends(get_doctor_query_port)]


def get_vital_signs_query_service(
    vital_signs_repository: VitalSignsRepo,
) -> VisitVitalSignsQueryService:
    return VisitVitalSignsQueryService(vital_signs_repository=vital_signs_repository)


def get_record_vital_signs_use_case(
    vital_signs_repository: VitalSignsRepo,
    visit_query_port: VisitPort,
    doctor_query_port: DoctorPort,
    unit_of_work: Uow,
) -> RecordVisitVitalSigns:
    return RecordVisitVitalSigns(
        vital_signs_repository=vital_signs_repository,
        visit_query_port=visit_query_port,
        doctor_query_port=doctor_query_port,
        unit_of_work=unit_of_work,
    )
