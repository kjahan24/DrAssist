"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring `api/router.py` `Depends()`s on. Every
provider ultimately depends on `app.api.deps.get_db_session`, so all
repositories constructed for one request share the same `AsyncSession`
(and therefore the same transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`UploadMedicalDocument` needs the Patient, Visit, and Appointment
modules' public facades; each is built via its own
`build_patient_facade`/`build_visit_facade`/`build_appointment_facade`
composition root (bound to the same `session`) rather than duplicating
facade construction here — the same pattern
`app.modules.attachments.api.dependencies` established.

`get_storage_port` is `@lru_cache`d and takes no `session` — unlike the
repositories above, `LocalStorageProvider` is stateless filesystem I/O
with no per-request transaction to join, the same reasoning
`app.infrastructure.storage.minio_client.get_minio_client` already
applies to the raw MinIO SDK client. `_storage_provider` is the
`StorageProvider` enum value recorded on every uploaded document — it
must be changed alongside `get_storage_port` if a future task swaps in a
real S3/Azure/GCS adapter (see `container.py`'s own scope note).
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.config import get_settings
from app.core.container import get_event_bus
from app.infrastructure.storage.local_storage_provider import LocalStorageProvider
from app.modules.appointment.container import build_appointment_facade
from app.modules.appointment.public.interfaces import AppointmentQueryPort
from app.modules.documents.application.services.document_query_service import (
    MedicalDocumentQueryService,
)
from app.modules.documents.application.use_cases.archive_medical_document import (
    ArchiveMedicalDocument,
)
from app.modules.documents.application.use_cases.delete_medical_document import (
    DeleteMedicalDocument,
)
from app.modules.documents.application.use_cases.download_medical_document import (
    DownloadMedicalDocument,
)
from app.modules.documents.application.use_cases.update_medical_document_details import (
    UpdateMedicalDocumentDetails,
)
from app.modules.documents.application.use_cases.upload_medical_document import (
    UploadMedicalDocument,
)
from app.modules.documents.domain.enums import StorageProvider
from app.modules.documents.domain.repositories import MedicalDocumentRepository
from app.modules.documents.infrastructure.repositories import SqlAlchemyMedicalDocumentRepository
from app.modules.patient.container import build_patient_facade
from app.modules.patient.public.interfaces import PatientQueryPort
from app.modules.visit.container import build_visit_facade
from app.modules.visit.public.interfaces import VisitQueryPort
from app.shared.application.storage_port import StoragePort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork

_ACTIVE_STORAGE_PROVIDER = StorageProvider.LOCAL


def get_document_repository(session: DbSession) -> MedicalDocumentRepository:
    return SqlAlchemyMedicalDocumentRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_patient_query_port(session: DbSession) -> PatientQueryPort:
    return build_patient_facade(session)


def get_visit_query_port(session: DbSession) -> VisitQueryPort:
    return build_visit_facade(session)


def get_appointment_query_port(session: DbSession) -> AppointmentQueryPort:
    return build_appointment_facade(session)


@lru_cache
def get_storage_port() -> StoragePort:
    return LocalStorageProvider(get_settings().local_storage.base_path)


DocumentRepo = Annotated[MedicalDocumentRepository, Depends(get_document_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
PatientPort = Annotated[PatientQueryPort, Depends(get_patient_query_port)]
VisitPort = Annotated[VisitQueryPort, Depends(get_visit_query_port)]
AppointmentPort = Annotated[AppointmentQueryPort, Depends(get_appointment_query_port)]
Storage = Annotated[StoragePort, Depends(get_storage_port)]


def get_document_query_service(document_repository: DocumentRepo) -> MedicalDocumentQueryService:
    return MedicalDocumentQueryService(document_repository=document_repository)


def get_upload_medical_document_use_case(
    document_repository: DocumentRepo,
    patient_query_port: PatientPort,
    visit_query_port: VisitPort,
    appointment_query_port: AppointmentPort,
    storage: Storage,
    unit_of_work: Uow,
) -> UploadMedicalDocument:
    return UploadMedicalDocument(
        document_repository=document_repository,
        patient_query_port=patient_query_port,
        visit_query_port=visit_query_port,
        appointment_query_port=appointment_query_port,
        storage=storage,
        storage_provider=_ACTIVE_STORAGE_PROVIDER,
        unit_of_work=unit_of_work,
    )


def get_update_medical_document_details_use_case(
    document_repository: DocumentRepo, unit_of_work: Uow
) -> UpdateMedicalDocumentDetails:
    return UpdateMedicalDocumentDetails(
        document_repository=document_repository, unit_of_work=unit_of_work
    )


def get_archive_medical_document_use_case(
    document_repository: DocumentRepo, unit_of_work: Uow
) -> ArchiveMedicalDocument:
    return ArchiveMedicalDocument(
        document_repository=document_repository, unit_of_work=unit_of_work
    )


def get_delete_medical_document_use_case(
    document_repository: DocumentRepo, unit_of_work: Uow
) -> DeleteMedicalDocument:
    return DeleteMedicalDocument(document_repository=document_repository, unit_of_work=unit_of_work)


def get_download_medical_document_use_case(
    document_repository: DocumentRepo, storage: Storage
) -> DownloadMedicalDocument:
    return DownloadMedicalDocument(document_repository=document_repository, storage=storage)
