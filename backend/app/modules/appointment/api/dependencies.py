"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`CreateAppointment`/`CompleteAppointment` need four peer modules' public
facades (Patient, Doctor, Authentication, Visit), each built via its own
composition root (`build_..._facade`, bound to the same `session`)
rather than duplicating facade construction here — the same pattern
`app.modules.doctor_review.api.dependencies` established for its own
peer-module facades.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.appointment.application.services.appointment_consistency_service import (
    AppointmentConsistencyService,
)
from app.modules.appointment.application.services.appointment_query_service import (
    AppointmentQueryService,
)
from app.modules.appointment.application.use_cases.cancel_appointment import CancelAppointment
from app.modules.appointment.application.use_cases.check_in_appointment import (
    CheckInAppointment,
)
from app.modules.appointment.application.use_cases.complete_appointment import (
    CompleteAppointment,
)
from app.modules.appointment.application.use_cases.confirm_appointment import ConfirmAppointment
from app.modules.appointment.application.use_cases.create_appointment import CreateAppointment
from app.modules.appointment.application.use_cases.mark_appointment_no_show import (
    MarkAppointmentNoShow,
)
from app.modules.appointment.application.use_cases.start_appointment import StartAppointment
from app.modules.appointment.application.use_cases.update_appointment import UpdateAppointment
from app.modules.appointment.domain.repositories import AppointmentRepository
from app.modules.appointment.infrastructure.repositories import SqlAlchemyAppointmentRepository
from app.modules.authentication.container import build_authentication_facade
from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.doctor.container import build_doctor_facade
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.patient.container import build_patient_facade
from app.modules.patient.public.interfaces import PatientQueryPort
from app.modules.visit.container import build_visit_facade
from app.modules.visit.public.interfaces import VisitQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_appointment_repository(session: DbSession) -> AppointmentRepository:
    return SqlAlchemyAppointmentRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_patient_query_port(session: DbSession) -> PatientQueryPort:
    return build_patient_facade(session)


def get_doctor_query_port(session: DbSession) -> DoctorQueryPort:
    return build_doctor_facade(session)


def get_user_query_port(session: DbSession) -> UserQueryPort:
    return build_authentication_facade(session)


def get_visit_query_port(session: DbSession) -> VisitQueryPort:
    return build_visit_facade(session)


AppointmentRepo = Annotated[AppointmentRepository, Depends(get_appointment_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
PatientPort = Annotated[PatientQueryPort, Depends(get_patient_query_port)]
DoctorPort = Annotated[DoctorQueryPort, Depends(get_doctor_query_port)]
UserPort = Annotated[UserQueryPort, Depends(get_user_query_port)]
VisitPort = Annotated[VisitQueryPort, Depends(get_visit_query_port)]


def get_appointment_query_service(
    appointment_repository: AppointmentRepo,
) -> AppointmentQueryService:
    return AppointmentQueryService(appointment_repository=appointment_repository)


def get_appointment_consistency_service(
    patient_query_port: PatientPort,
    doctor_query_port: DoctorPort,
    user_query_port: UserPort,
    visit_query_port: VisitPort,
) -> AppointmentConsistencyService:
    return AppointmentConsistencyService(
        patient_query_port=patient_query_port,
        doctor_query_port=doctor_query_port,
        user_query_port=user_query_port,
        visit_query_port=visit_query_port,
    )


ConsistencyService = Annotated[
    AppointmentConsistencyService, Depends(get_appointment_consistency_service)
]


def get_create_appointment_use_case(
    appointment_repository: AppointmentRepo,
    consistency_service: ConsistencyService,
    unit_of_work: Uow,
) -> CreateAppointment:
    return CreateAppointment(
        appointment_repository=appointment_repository,
        consistency_service=consistency_service,
        unit_of_work=unit_of_work,
    )


def get_update_appointment_use_case(
    appointment_repository: AppointmentRepo, unit_of_work: Uow
) -> UpdateAppointment:
    return UpdateAppointment(
        appointment_repository=appointment_repository, unit_of_work=unit_of_work
    )


def get_confirm_appointment_use_case(
    appointment_repository: AppointmentRepo, unit_of_work: Uow
) -> ConfirmAppointment:
    return ConfirmAppointment(
        appointment_repository=appointment_repository, unit_of_work=unit_of_work
    )


def get_check_in_appointment_use_case(
    appointment_repository: AppointmentRepo, unit_of_work: Uow
) -> CheckInAppointment:
    return CheckInAppointment(
        appointment_repository=appointment_repository, unit_of_work=unit_of_work
    )


def get_start_appointment_use_case(
    appointment_repository: AppointmentRepo, unit_of_work: Uow
) -> StartAppointment:
    return StartAppointment(
        appointment_repository=appointment_repository, unit_of_work=unit_of_work
    )


def get_complete_appointment_use_case(
    appointment_repository: AppointmentRepo,
    consistency_service: ConsistencyService,
    unit_of_work: Uow,
) -> CompleteAppointment:
    return CompleteAppointment(
        appointment_repository=appointment_repository,
        consistency_service=consistency_service,
        unit_of_work=unit_of_work,
    )


def get_cancel_appointment_use_case(
    appointment_repository: AppointmentRepo, unit_of_work: Uow
) -> CancelAppointment:
    return CancelAppointment(
        appointment_repository=appointment_repository, unit_of_work=unit_of_work
    )


def get_mark_appointment_no_show_use_case(
    appointment_repository: AppointmentRepo, unit_of_work: Uow
) -> MarkAppointmentNoShow:
    return MarkAppointmentNoShow(
        appointment_repository=appointment_repository, unit_of_work=unit_of_work
    )
