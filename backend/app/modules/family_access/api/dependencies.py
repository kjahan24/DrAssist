"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring `api/router.py` `Depends()`s on. Every
provider ultimately depends on `app.api.deps.get_db_session`, so all
repositories constructed for one request share the same `AsyncSession`
(and therefore the same transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`InviteCaregiver` needs the Patient and Authentication modules' public
facades, each built via its own `build_patient_facade`/
`build_authentication_facade` composition root (bound to the same
`session`) rather than duplicating facade construction here — the same
pattern `app.modules.documents.api.dependencies` established.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.authentication.container import build_authentication_facade
from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.family_access.application.services.family_access_query_service import (
    FamilyAccessQueryService,
)
from app.modules.family_access.application.use_cases.accept_invitation import AcceptInvitation
from app.modules.family_access.application.use_cases.invite_caregiver import InviteCaregiver
from app.modules.family_access.application.use_cases.reject_invitation import RejectInvitation
from app.modules.family_access.application.use_cases.revoke_access import RevokeAccess
from app.modules.family_access.domain.repositories import FamilyAccessRepository
from app.modules.family_access.infrastructure.repositories import (
    SqlAlchemyFamilyAccessRepository,
)
from app.modules.patient.container import build_patient_facade
from app.modules.patient.public.interfaces import PatientQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_family_access_repository(session: DbSession) -> FamilyAccessRepository:
    return SqlAlchemyFamilyAccessRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_patient_query_port(session: DbSession) -> PatientQueryPort:
    return build_patient_facade(session)


def get_user_query_port(session: DbSession) -> UserQueryPort:
    return build_authentication_facade(session)


FamilyAccessRepo = Annotated[FamilyAccessRepository, Depends(get_family_access_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
PatientPort = Annotated[PatientQueryPort, Depends(get_patient_query_port)]
UserPort = Annotated[UserQueryPort, Depends(get_user_query_port)]


def get_family_access_query_service(
    family_access_repository: FamilyAccessRepo,
) -> FamilyAccessQueryService:
    return FamilyAccessQueryService(family_access_repository=family_access_repository)


def get_invite_caregiver_use_case(
    family_access_repository: FamilyAccessRepo,
    patient_query_port: PatientPort,
    user_query_port: UserPort,
    unit_of_work: Uow,
) -> InviteCaregiver:
    return InviteCaregiver(
        family_access_repository=family_access_repository,
        patient_query_port=patient_query_port,
        user_query_port=user_query_port,
        unit_of_work=unit_of_work,
    )


def get_accept_invitation_use_case(
    family_access_repository: FamilyAccessRepo, unit_of_work: Uow
) -> AcceptInvitation:
    return AcceptInvitation(
        family_access_repository=family_access_repository, unit_of_work=unit_of_work
    )


def get_reject_invitation_use_case(
    family_access_repository: FamilyAccessRepo, unit_of_work: Uow
) -> RejectInvitation:
    return RejectInvitation(
        family_access_repository=family_access_repository, unit_of_work=unit_of_work
    )


def get_revoke_access_use_case(
    family_access_repository: FamilyAccessRepo, unit_of_work: Uow
) -> RevokeAccess:
    return RevokeAccess(
        family_access_repository=family_access_repository, unit_of_work=unit_of_work
    )
