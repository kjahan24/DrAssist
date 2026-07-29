"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`UploadVisitAttachment` needs both the Visit and Doctor modules' public
facades; both are built via their own `build_visit_facade`/
`build_doctor_facade` composition roots (bound to the same `session`)
rather than duplicating facade construction here — the same pattern
`app.modules.procedures.api.dependencies` established.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.attachments.application.services.attachment_query_service import (
    VisitAttachmentQueryService,
)
from app.modules.attachments.application.use_cases.upload_attachment import (
    UploadVisitAttachment,
)
from app.modules.attachments.domain.repositories import VisitAttachmentRepository
from app.modules.attachments.infrastructure.repositories import (
    SqlAlchemyVisitAttachmentRepository,
)
from app.modules.doctor.container import build_doctor_facade
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.visit.container import build_visit_facade
from app.modules.visit.public.interfaces import VisitQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_attachment_repository(session: DbSession) -> VisitAttachmentRepository:
    return SqlAlchemyVisitAttachmentRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_visit_query_port(session: DbSession) -> VisitQueryPort:
    return build_visit_facade(session)


def get_doctor_query_port(session: DbSession) -> DoctorQueryPort:
    return build_doctor_facade(session)


AttachmentRepo = Annotated[VisitAttachmentRepository, Depends(get_attachment_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
VisitPort = Annotated[VisitQueryPort, Depends(get_visit_query_port)]
DoctorPort = Annotated[DoctorQueryPort, Depends(get_doctor_query_port)]


def get_attachment_query_service(
    attachment_repository: AttachmentRepo,
) -> VisitAttachmentQueryService:
    return VisitAttachmentQueryService(attachment_repository=attachment_repository)


def get_upload_attachment_use_case(
    attachment_repository: AttachmentRepo,
    visit_query_port: VisitPort,
    doctor_query_port: DoctorPort,
    unit_of_work: Uow,
) -> UploadVisitAttachment:
    return UploadVisitAttachment(
        attachment_repository=attachment_repository,
        visit_query_port=visit_query_port,
        doctor_query_port=doctor_query_port,
        unit_of_work=unit_of_work,
    )
