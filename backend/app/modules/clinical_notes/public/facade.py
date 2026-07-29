"""`ClinicalNoteFacade` — the one concrete implementation of
`ClinicalNoteQueryPort`. Constructed per-request by
`app.modules.clinical_notes.container.build_clinical_note_facade`, bound
to that request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.clinical_notes.application.services.clinical_note_query_service import (
    ClinicalNoteQueryService,
)
from app.modules.clinical_notes.public.dto import ClinicalNoteSummaryDTO
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort


class ClinicalNoteFacade(ClinicalNoteQueryPort):
    def __init__(self, *, query_service: ClinicalNoteQueryService) -> None:
        self._query_service = query_service

    async def clinical_note_exists(self, clinical_note_id: UUID) -> bool:
        return await self._query_service.clinical_note_exists(clinical_note_id)

    async def get_clinical_note_summary(
        self, clinical_note_id: UUID
    ) -> ClinicalNoteSummaryDTO | None:
        return await self._query_service.get_clinical_note_summary(clinical_note_id)

    async def list_clinical_notes_for_visit(self, visit_id: UUID) -> list[ClinicalNoteSummaryDTO]:
        return await self._query_service.list_clinical_notes_for_visit(visit_id)

    async def list_clinical_notes_for_patient(
        self, patient_id: UUID
    ) -> list[ClinicalNoteSummaryDTO]:
        return await self._query_service.list_clinical_notes_for_patient(patient_id)
