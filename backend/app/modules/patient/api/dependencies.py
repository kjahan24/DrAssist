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
from app.modules.patient.application.use_cases.add_emergency_contact import AddEmergencyContact
from app.modules.patient.application.use_cases.add_insurance import AddInsurance
from app.modules.patient.application.use_cases.add_patient_contact import AddPatientContact
from app.modules.patient.application.use_cases.register_patient import RegisterPatient
from app.modules.patient.domain.repositories import (
    EmergencyContactRepository,
    InsuranceRepository,
    PatientContactRepository,
    PatientRepository,
)
from app.modules.patient.infrastructure.repositories import (
    SqlAlchemyEmergencyContactRepository,
    SqlAlchemyInsuranceRepository,
    SqlAlchemyPatientContactRepository,
    SqlAlchemyPatientRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_patient_repository(session: DbSession) -> PatientRepository:
    return SqlAlchemyPatientRepository(session)


def get_patient_contact_repository(session: DbSession) -> PatientContactRepository:
    return SqlAlchemyPatientContactRepository(session)


def get_emergency_contact_repository(session: DbSession) -> EmergencyContactRepository:
    return SqlAlchemyEmergencyContactRepository(session)


def get_insurance_repository(session: DbSession) -> InsuranceRepository:
    return SqlAlchemyInsuranceRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_organization_query_port(session: DbSession) -> OrganizationQueryPort:
    return build_organization_facade(session)


PatientRepo = Annotated[PatientRepository, Depends(get_patient_repository)]
PatientContactRepo = Annotated[PatientContactRepository, Depends(get_patient_contact_repository)]
EmergencyContactRepo = Annotated[
    EmergencyContactRepository, Depends(get_emergency_contact_repository)
]
InsuranceRepo = Annotated[InsuranceRepository, Depends(get_insurance_repository)]
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


def get_add_patient_contact_use_case(
    patient_contact_repository: PatientContactRepo,
    patient_repository: PatientRepo,
    unit_of_work: Uow,
) -> AddPatientContact:
    return AddPatientContact(
        patient_contact_repository=patient_contact_repository,
        patient_repository=patient_repository,
        unit_of_work=unit_of_work,
    )


def get_add_emergency_contact_use_case(
    emergency_contact_repository: EmergencyContactRepo,
    patient_repository: PatientRepo,
    unit_of_work: Uow,
) -> AddEmergencyContact:
    return AddEmergencyContact(
        emergency_contact_repository=emergency_contact_repository,
        patient_repository=patient_repository,
        unit_of_work=unit_of_work,
    )


def get_add_insurance_use_case(
    insurance_repository: InsuranceRepo,
    patient_repository: PatientRepo,
    unit_of_work: Uow,
) -> AddInsurance:
    return AddInsurance(
        insurance_repository=insurance_repository,
        patient_repository=patient_repository,
        unit_of_work=unit_of_work,
    )
