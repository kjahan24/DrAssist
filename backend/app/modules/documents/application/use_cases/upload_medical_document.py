"""`UploadMedicalDocument` — orchestrates the module's only file-write
path: validate the referenced Patient/Visit/Appointment, generate a
unique `stored_filename`, hand the bytes to the configured `StoragePort`
adapter, then persist the resulting metadata row.

A document always references an existing `Patient`; `organization_id` is
derived from the patient's own summary (never accepted as a separate,
independently trustable input) — the same cross-module dependency
pattern `app.modules.attachments.application.use_cases.upload_attachment
.UploadVisitAttachment` established for `Visit`. When `visit_id`/
`appointment_id` are given, each is resolved through its own public port
and checked against *both* `organization_id` and `patient_id` — this
task's Validation section names "Visit ownership"/"Appointment
ownership" as checks distinct from mere existence, so a visit or
appointment that exists but belongs to a different patient/organization
raises `VisitOwnershipMismatchError`/`AppointmentOwnershipMismatchError`
rather than being silently accepted or treated as not-found.

`stored_filename` is system-generated (a UUID4 hex plus the original
extension), never user-supplied — the only way to actually guarantee
"stored filename must be unique" as a real invariant;
`get_by_stored_filename` is still checked defensively per this task's own
"Duplicate stored filename" validation rule, even though a UUID4
collision is astronomically unlikely.

`storage_provider` is injected at construction time (wired in
`container.py` from whichever concrete `StoragePort` adapter is
configured — `LocalStorageProvider` today), not derived from the
request: the caller has no way to know or choose it, since only one
adapter is ever active per deployment (see `domain/enums.py::StorageProvider`).

The entity starts `Uploading` and is moved to `Active` only after
`storage.upload()` returns successfully — if the surrounding transaction
then fails, the ORM insert simply never happens; there is no orphaned
storage cleanup in this task's scope (no background jobs — see this
task's own exclusions).
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.appointment.public.interfaces import AppointmentQueryPort
from app.modules.documents.application.constants import DOCUMENT_STORAGE_BUCKET
from app.modules.documents.application.dto import (
    UploadMedicalDocumentInput,
    UploadMedicalDocumentOutput,
)
from app.modules.documents.domain.entities import MedicalDocument
from app.modules.documents.domain.enums import StorageProvider
from app.modules.documents.domain.exceptions import (
    AppointmentNotFoundError,
    AppointmentOwnershipMismatchError,
    DuplicateStoredFilenameError,
    PatientNotFoundError,
    VisitNotFoundError,
    VisitOwnershipMismatchError,
)
from app.modules.documents.domain.repositories import MedicalDocumentRepository
from app.modules.documents.domain.value_objects import Sha256Checksum
from app.modules.patient.public.interfaces import PatientQueryPort
from app.modules.visit.public.interfaces import VisitQueryPort
from app.shared.application.storage_port import StoragePort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UploadMedicalDocument(UseCase[UploadMedicalDocumentInput, UploadMedicalDocumentOutput]):
    def __init__(
        self,
        *,
        document_repository: MedicalDocumentRepository,
        patient_query_port: PatientQueryPort,
        visit_query_port: VisitQueryPort,
        appointment_query_port: AppointmentQueryPort,
        storage: StoragePort,
        storage_provider: StorageProvider,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._documents = document_repository
        self._patients = patient_query_port
        self._visits = visit_query_port
        self._appointments = appointment_query_port
        self._storage = storage
        self._storage_provider = storage_provider
        self._uow = unit_of_work

    async def execute(self, input_dto: UploadMedicalDocumentInput) -> UploadMedicalDocumentOutput:
        patient_summary = await self._patients.get_patient_summary(input_dto.patient_id)
        if patient_summary is None:
            raise PatientNotFoundError(input_dto.patient_id)
        organization_id = patient_summary.organization_id

        if input_dto.visit_id is not None:
            visit_summary = await self._visits.get_visit_summary(input_dto.visit_id)
            if visit_summary is None:
                raise VisitNotFoundError(input_dto.visit_id)
            if (
                visit_summary.organization_id != organization_id
                or visit_summary.patient_id != input_dto.patient_id
            ):
                raise VisitOwnershipMismatchError(input_dto.visit_id)

        if input_dto.appointment_id is not None:
            appointment_summary = await self._appointments.get_appointment_summary(
                input_dto.appointment_id
            )
            if appointment_summary is None:
                raise AppointmentNotFoundError(input_dto.appointment_id)
            if (
                appointment_summary.organization_id != organization_id
                or appointment_summary.patient_id != input_dto.patient_id
            ):
                raise AppointmentOwnershipMismatchError(input_dto.appointment_id)

        checksum = Sha256Checksum(input_dto.checksum_sha256)
        stored_filename = f"{uuid4().hex}{input_dto.extension}"
        if await self._documents.get_by_stored_filename(stored_filename) is not None:
            raise DuplicateStoredFilenameError(stored_filename)

        storage_path = await self._storage.upload(
            bucket=DOCUMENT_STORAGE_BUCKET,
            object_name=stored_filename,
            data=input_dto.file_data,
            content_type=input_dto.mime_type,
        )

        document = MedicalDocument.create(
            organization_id=organization_id,
            patient_id=input_dto.patient_id,
            uploaded_by_user_id=input_dto.uploaded_by_user_id,
            visit_id=input_dto.visit_id,
            appointment_id=input_dto.appointment_id,
            category=input_dto.category,
            title=input_dto.title,
            original_filename=input_dto.original_filename,
            stored_filename=stored_filename,
            mime_type=input_dto.mime_type,
            extension=input_dto.extension,
            file_size_bytes=input_dto.file_size_bytes,
            storage_provider=self._storage_provider,
            storage_path=storage_path,
            checksum_sha256=checksum,
            uploaded_at=datetime.now(UTC),
            description=input_dto.description,
            tags=input_dto.tags,
            metadata=input_dto.metadata,
        )
        document.activate()

        await self._documents.add(document)
        self._uow.collect_events(document.pull_events())
        await self._uow.commit()

        return UploadMedicalDocumentOutput(
            document_id=document.id,
            organization_id=document.organization_id,
            patient_id=document.patient_id,
            stored_filename=document.stored_filename,
            storage_path=document.storage_path,
        )
