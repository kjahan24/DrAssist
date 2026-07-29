"""`UploadVisitAttachment` — an attachment always references an existing
visit, and both its `storage_key` and `checksum_sha256` must be unique
across the whole table (not merely within a visit — the business rules
state "storage_key must be unique" and "checksum_sha256 must be unique"
with no "within a Visit" qualifier, unlike every prior module's
`sequence_number` rule). The `checksum_sha256` uniqueness in particular
is a genuine content-addressable dedup constraint: the identical file
cannot be attached twice anywhere in the system, even to different
visits or organizations — taken literally from the stated rule rather
than narrowed to a per-visit or per-organization scope that isn't
written anywhere in this task.

Unlike the Patient module's sub-resource use cases (which read the parent
`Patient` from a same-module repository), `VisitAttachment` references
`Visit` as a peer module — so it is resolved through its public facade
(`VisitQueryPort`), the same cross-module dependency pattern
`app.modules.procedures.application.use_cases.record_procedure.RecordVisitProcedure`
established for this codebase. `organization_id` is derived from the
visit's own summary (never accepted as a separate, independently
trustable input). A missing visit raises `PatientVisitNotFoundError`
directly, reused rather than wrapped (see
`docs/backend-architecture/10_module_communication.md`).

When `uploaded_by` is provided, it is resolved via `get_doctor_summary`
(not the cheaper `doctor_exists`) so its `organization_id` can be
compared against the visit's: a doctor belonging to a *different*
organization is treated identically to a missing one —
`DoctorNotFoundError`, never a distinct "wrong organization" error — the
same cross-tenant-as-not-found pattern every prior Visit sub-module
already established.
"""

from app.modules.attachments.application.dto import (
    UploadVisitAttachmentInput,
    UploadVisitAttachmentOutput,
)
from app.modules.attachments.domain.entities import VisitAttachment
from app.modules.attachments.domain.exceptions import (
    DuplicateChecksumError,
    DuplicateStorageKeyError,
)
from app.modules.attachments.domain.repositories import VisitAttachmentRepository
from app.modules.attachments.domain.value_objects import Sha256Checksum
from app.modules.doctor.domain.exceptions import DoctorNotFoundError
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.visit.domain.exceptions import PatientVisitNotFoundError
from app.modules.visit.public.interfaces import VisitQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UploadVisitAttachment(UseCase[UploadVisitAttachmentInput, UploadVisitAttachmentOutput]):
    def __init__(
        self,
        *,
        attachment_repository: VisitAttachmentRepository,
        visit_query_port: VisitQueryPort,
        doctor_query_port: DoctorQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._attachments = attachment_repository
        self._visits = visit_query_port
        self._doctors = doctor_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: UploadVisitAttachmentInput) -> UploadVisitAttachmentOutput:
        visit_summary = await self._visits.get_visit_summary(input_dto.visit_id)
        if visit_summary is None:
            raise PatientVisitNotFoundError(input_dto.visit_id)

        if input_dto.uploaded_by is not None:
            doctor_summary = await self._doctors.get_doctor_summary(input_dto.uploaded_by)
            if (
                doctor_summary is None
                or doctor_summary.organization_id != visit_summary.organization_id
            ):
                raise DoctorNotFoundError(input_dto.uploaded_by)

        existing_key = await self._attachments.get_by_storage_key(input_dto.storage_key)
        if existing_key is not None:
            raise DuplicateStorageKeyError(input_dto.storage_key)

        checksum = Sha256Checksum(input_dto.checksum_sha256)
        existing_checksum = await self._attachments.get_by_checksum(checksum)
        if existing_checksum is not None:
            raise DuplicateChecksumError(str(checksum))

        attachment = VisitAttachment.create(
            organization_id=visit_summary.organization_id,
            visit_id=input_dto.visit_id,
            attachment_type=input_dto.attachment_type,
            file_name=input_dto.file_name,
            original_file_name=input_dto.original_file_name,
            mime_type=input_dto.mime_type,
            file_size_bytes=input_dto.file_size_bytes,
            storage_provider=input_dto.storage_provider,
            storage_bucket=input_dto.storage_bucket,
            storage_key=input_dto.storage_key,
            checksum_sha256=checksum,
            uploaded_at=input_dto.uploaded_at,
            uploaded_by=input_dto.uploaded_by,
            description=input_dto.description,
        )
        await self._attachments.add(attachment)
        self._uow.collect_events(attachment.pull_events())
        await self._uow.commit()

        return UploadVisitAttachmentOutput(
            attachment_id=attachment.id,
            organization_id=attachment.organization_id,
            visit_id=attachment.visit_id,
            storage_key=attachment.storage_key,
        )
