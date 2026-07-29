"""Module composition root.

The one place `AttachmentQueryPort` gets bound to its concrete
implementation (`AttachmentFacade`), and the repository interface gets
bound to its SQLAlchemy implementation. Any future module's
`api/dependencies.py` calls `build_attachment_facade(session)` rather
than constructing `AttachmentFacade` (or the repository) directly.

Scope note — this task builds the Attachments module's **foundation**
only: the `VisitAttachment` entity, its repository, `UploadVisitAttachment`
(which confirms the referenced visit exists via the Visit module's
public facade, that `uploaded_by` — when supplied — references a doctor
in the same organization, and that `storage_key`/`checksum_sha256` are
each globally unique, before recording an attachment's metadata), and
the public query facade. It deliberately does **not** build any HTTP
endpoint, does not perform any actual file transfer to object storage
(this table stores metadata only), and does not modify the
Authentication, Organization, Doctor, Patient, Visit, Vital Signs, Chief
Complaints, Diagnosis, or Procedures modules or their tables. Clinical
Notes, SOAP Notes, Prescriptions, Lab Orders, Billing, and AI are
explicitly out of scope for this task.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attachments.application.services.attachment_query_service import (
    VisitAttachmentQueryService,
)
from app.modules.attachments.infrastructure.repositories import (
    SqlAlchemyVisitAttachmentRepository,
)
from app.modules.attachments.public.facade import AttachmentFacade


def build_attachment_facade(session: AsyncSession) -> AttachmentFacade:
    """Construct an `AttachmentFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so they participate in the same transaction
    as the rest of that request's work.
    """
    attachment_repository = SqlAlchemyVisitAttachmentRepository(session)

    query_service = VisitAttachmentQueryService(attachment_repository=attachment_repository)

    return AttachmentFacade(query_service=query_service)
