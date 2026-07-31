"""Read-only queries against `MedicalDocument`.

Backs the module's public `DocumentQueryPort` — the one implementation,
per `docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

`checksum_sha256` is coerced to `str` (the DTO boundary already treats it
as a primitive, matching `application/dto.py`'s own documented
convention).
"""

from uuid import UUID

from app.modules.documents.application.dto import MedicalDocumentSummaryDTO
from app.modules.documents.domain.entities import MedicalDocument
from app.modules.documents.domain.repositories import MedicalDocumentRepository


class MedicalDocumentQueryService:
    def __init__(self, *, document_repository: MedicalDocumentRepository) -> None:
        self._documents = document_repository

    async def document_exists(self, document_id: UUID) -> bool:
        return await self._documents.get_by_id(document_id) is not None

    async def get_document_summary(self, document_id: UUID) -> MedicalDocumentSummaryDTO | None:
        document = await self._documents.get_by_id(document_id)
        return _to_summary(document) if document is not None else None

    async def list_documents_for_patient(self, patient_id: UUID) -> list[MedicalDocumentSummaryDTO]:
        documents = await self._documents.list_by_patient(patient_id)
        return [_to_summary(document) for document in documents]

    async def list_documents_for_visit(self, visit_id: UUID) -> list[MedicalDocumentSummaryDTO]:
        documents = await self._documents.list_by_visit(visit_id)
        return [_to_summary(document) for document in documents]

    async def list_documents_for_appointment(
        self, appointment_id: UUID
    ) -> list[MedicalDocumentSummaryDTO]:
        documents = await self._documents.list_by_appointment(appointment_id)
        return [_to_summary(document) for document in documents]


def _to_summary(document: MedicalDocument) -> MedicalDocumentSummaryDTO:
    return MedicalDocumentSummaryDTO(
        document_id=document.id,
        organization_id=document.organization_id,
        patient_id=document.patient_id,
        uploaded_by_user_id=document.uploaded_by_user_id,
        visit_id=document.visit_id,
        appointment_id=document.appointment_id,
        category=document.category,
        title=document.title,
        original_filename=document.original_filename,
        stored_filename=document.stored_filename,
        mime_type=document.mime_type,
        extension=document.extension,
        file_size_bytes=document.file_size_bytes,
        storage_provider=document.storage_provider,
        storage_path=document.storage_path,
        checksum_sha256=str(document.checksum_sha256),
        status=document.status,
        uploaded_at=document.uploaded_at,
        description=document.description,
        tags=document.tags,
        metadata=document.metadata,
    )
