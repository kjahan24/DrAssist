"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`CreateDoctorSchedule`/`CreateDoctorTimeOff` need the Doctor module's
public facade (via `ScheduleConsistencyService`), built via its own
composition root (`build_doctor_facade`, bound to the same `session`)
rather than duplicating facade construction here — the same pattern
`app.modules.appointment.api.dependencies` established for its own
peer-module facades.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.doctor.container import build_doctor_facade
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.schedule.application.services.doctor_schedule_query_service import (
    DoctorScheduleQueryService,
)
from app.modules.schedule.application.services.doctor_time_off_query_service import (
    DoctorTimeOffQueryService,
)
from app.modules.schedule.application.services.schedule_consistency_service import (
    ScheduleConsistencyService,
)
from app.modules.schedule.application.use_cases.activate_doctor_schedule import (
    ActivateDoctorSchedule,
)
from app.modules.schedule.application.use_cases.create_doctor_schedule import (
    CreateDoctorSchedule,
)
from app.modules.schedule.application.use_cases.create_doctor_time_off import (
    CreateDoctorTimeOff,
)
from app.modules.schedule.application.use_cases.deactivate_doctor_schedule import (
    DeactivateDoctorSchedule,
)
from app.modules.schedule.application.use_cases.update_doctor_schedule import (
    UpdateDoctorSchedule,
)
from app.modules.schedule.application.use_cases.update_doctor_time_off import (
    UpdateDoctorTimeOff,
)
from app.modules.schedule.domain.repositories import (
    DoctorScheduleRepository,
    DoctorTimeOffRepository,
)
from app.modules.schedule.infrastructure.repositories import (
    SqlAlchemyDoctorScheduleRepository,
    SqlAlchemyDoctorTimeOffRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_doctor_schedule_repository(session: DbSession) -> DoctorScheduleRepository:
    return SqlAlchemyDoctorScheduleRepository(session)


def get_doctor_time_off_repository(session: DbSession) -> DoctorTimeOffRepository:
    return SqlAlchemyDoctorTimeOffRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_doctor_query_port(session: DbSession) -> DoctorQueryPort:
    return build_doctor_facade(session)


DoctorScheduleRepo = Annotated[DoctorScheduleRepository, Depends(get_doctor_schedule_repository)]
DoctorTimeOffRepo = Annotated[DoctorTimeOffRepository, Depends(get_doctor_time_off_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
DoctorPort = Annotated[DoctorQueryPort, Depends(get_doctor_query_port)]


def get_schedule_consistency_service(
    doctor_query_port: DoctorPort,
) -> ScheduleConsistencyService:
    return ScheduleConsistencyService(doctor_query_port=doctor_query_port)


ConsistencyService = Annotated[
    ScheduleConsistencyService, Depends(get_schedule_consistency_service)
]


def get_doctor_schedule_query_service(
    doctor_schedule_repository: DoctorScheduleRepo,
) -> DoctorScheduleQueryService:
    return DoctorScheduleQueryService(doctor_schedule_repository=doctor_schedule_repository)


def get_doctor_time_off_query_service(
    doctor_time_off_repository: DoctorTimeOffRepo,
) -> DoctorTimeOffQueryService:
    return DoctorTimeOffQueryService(doctor_time_off_repository=doctor_time_off_repository)


def get_create_doctor_schedule_use_case(
    doctor_schedule_repository: DoctorScheduleRepo,
    consistency_service: ConsistencyService,
    unit_of_work: Uow,
) -> CreateDoctorSchedule:
    return CreateDoctorSchedule(
        doctor_schedule_repository=doctor_schedule_repository,
        consistency_service=consistency_service,
        unit_of_work=unit_of_work,
    )


def get_update_doctor_schedule_use_case(
    doctor_schedule_repository: DoctorScheduleRepo, unit_of_work: Uow
) -> UpdateDoctorSchedule:
    return UpdateDoctorSchedule(
        doctor_schedule_repository=doctor_schedule_repository, unit_of_work=unit_of_work
    )


def get_activate_doctor_schedule_use_case(
    doctor_schedule_repository: DoctorScheduleRepo, unit_of_work: Uow
) -> ActivateDoctorSchedule:
    return ActivateDoctorSchedule(
        doctor_schedule_repository=doctor_schedule_repository, unit_of_work=unit_of_work
    )


def get_deactivate_doctor_schedule_use_case(
    doctor_schedule_repository: DoctorScheduleRepo, unit_of_work: Uow
) -> DeactivateDoctorSchedule:
    return DeactivateDoctorSchedule(
        doctor_schedule_repository=doctor_schedule_repository, unit_of_work=unit_of_work
    )


def get_create_doctor_time_off_use_case(
    doctor_time_off_repository: DoctorTimeOffRepo,
    consistency_service: ConsistencyService,
    unit_of_work: Uow,
) -> CreateDoctorTimeOff:
    return CreateDoctorTimeOff(
        doctor_time_off_repository=doctor_time_off_repository,
        consistency_service=consistency_service,
        unit_of_work=unit_of_work,
    )


def get_update_doctor_time_off_use_case(
    doctor_time_off_repository: DoctorTimeOffRepo, unit_of_work: Uow
) -> UpdateDoctorTimeOff:
    return UpdateDoctorTimeOff(
        doctor_time_off_repository=doctor_time_off_repository, unit_of_work=unit_of_work
    )
