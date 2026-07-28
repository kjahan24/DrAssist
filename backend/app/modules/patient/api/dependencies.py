"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`RegisterPatient` additionally needs the Organization module's public
facade; that is built via its own `build_organization_facade`
composition root (bound to the same `session`) rather than duplicating
facade construction here — the same pattern
`app.modules.doctor.api.dependencies` established.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.organization.container import build_organization_facade
from app.modules.organization.public.interfaces import OrganizationQueryPort
from app.modules.patient.application.services.patient_query_service import PatientQueryService
from app.modules.patient.application.use_cases.register_patient import RegisterPatient
from app.modules.patient.domain.repositories import PatientRepository
from app.modules.patient.infrastructure.repositories import SqlAlchemyPatientRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_patient_repository(session: DbSession) -> PatientRepository:
    return SqlAlchemyPatientRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_organization_query_port(session: DbSession) -> OrganizationQueryPort:
    return build_organization_facade(session)


PatientRepo = Annotated[PatientRepository, Depends(get_patient_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
OrgQueryPort = Annotated[OrganizationQueryPort, Depends(get_organization_query_port)]


def get_patient_query_service(patient_repository: PatientRepo) -> PatientQueryService:
    return PatientQueryService(patient_repository=patient_repository)


def get_register_patient_use_case(
    patient_repository: PatientRepo,
    organization_query_port: OrgQueryPort,
    unit_of_work: Uow,
) -> RegisterPatient:
    return RegisterPatient(
        patient_repository=patient_repository,
        organization_query_port=organization_query_port,
        unit_of_work=unit_of_work,
    )
