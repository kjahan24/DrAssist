"""`DocumentFacade` — the one concrete implementation of
`DocumentQueryPort`. Constructed per-request by
`app.modules.documents.container.build_document_facade`, bound to that
request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.documents.application.services.document_query_service import (
    MedicalDocumentQueryService,
)
from app.modules.documents.public.dto import MedicalDocumentSummaryDTO
from app.modules.documents.public.interfaces import DocumentQueryPort


class DocumentFacade(DocumentQueryPort):
    def __init__(self, *, query_service: MedicalDocumentQueryService) -> None:
        self._query_service = query_service

    async def document_exists(self, document_id: UUID) -> bool:
        return await self._query_service.document_exists(document_id)

    async def get_document_summary(self, document_id: UUID) -> MedicalDocumentSummaryDTO | None:
        return await self._query_service.get_document_summary(document_id)

    async def list_documents_for_patient(self, patient_id: UUID) -> list[MedicalDocumentSummaryDTO]:
        return await self._query_service.list_documents_for_patient(patient_id)

    async def list_documents_for_visit(self, visit_id: UUID) -> list[MedicalDocumentSummaryDTO]:
        return await self._query_service.list_documents_for_visit(visit_id)

    async def list_documents_for_appointment(
        self, appointment_id: UUID
    ) -> list[MedicalDocumentSummaryDTO]:
        return await self._query_service.list_documents_for_appointment(appointment_id)
