"""Module composition root.

The one place `DocumentQueryPort` gets bound to its concrete
implementation (`DocumentFacade`), and the repository interface gets
bound to its SQLAlchemy implementation. Any future module's
`api/dependencies.py` calls `build_document_facade(session)` rather than
constructing `DocumentFacade` (or the repository) directly.

Scope note — this task builds the Documents module's **foundation**
only: the `MedicalDocument` aggregate (file *metadata* — see
`domain/entities.py`), its repository, `UploadMedicalDocument` (which
validates the referenced Patient/Visit/Appointment through their public
ports and writes the actual bytes via `StoragePort`),
`UpdateMedicalDocumentDetails`, `ArchiveMedicalDocument`,
`DeleteMedicalDocument`, `DownloadMedicalDocument`, and the public query
facade.

Storage is a provider **abstraction**: this task implements only
`LocalStorageProvider` (`app.infrastructure.storage.local_storage_provider`)
against the pre-existing shared `StoragePort`
(`app.shared.application.storage_port`); `StorageProvider.S3`/
`AZURE_BLOB`/`GOOGLE_CLOUD_STORAGE` are recorded as possible values on
`MedicalDocument.storage_provider` so a real adapter for each can be
wired in later purely by swapping which concrete `StoragePort`
implementation `api/dependencies.py` constructs — no schema change.

This module deliberately does **not** build any authentication or
authorization middleware, any cloud storage adapter (S3/Azure
Blob/GCS), OCR, AI document analysis, virus scanning, signed URLs,
encrypted storage, CDN integration, or background jobs (per this task's
explicit exclusions), and does not modify the Authentication,
Organization, Doctor, Patient, Visit, or Appointment modules or their
tables — it only *reads* three of them (Patient, Visit, Appointment)
through their public ports. Personal Health Timeline, Patient Portal,
Family/Caregiver Access, and Medical Community attachments are expected
to become their own consumers of `DocumentQueryPort`, the same way this
module itself depends on its three peer modules' ports.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.application.services.document_query_service import (
    MedicalDocumentQueryService,
)
from app.modules.documents.infrastructure.repositories import SqlAlchemyMedicalDocumentRepository
from app.modules.documents.public.facade import DocumentFacade


def build_document_facade(session: AsyncSession) -> DocumentFacade:
    """Construct a `DocumentFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so it participates in the same transaction
    as the rest of that request's work.
    """
    document_repository = SqlAlchemyMedicalDocumentRepository(session)

    query_service = MedicalDocumentQueryService(document_repository=document_repository)

    return DocumentFacade(query_service=query_service)
