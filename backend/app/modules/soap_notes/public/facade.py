"""`SOAPNoteFacade` — the one concrete implementation of
`SOAPNoteQueryPort`. Constructed per-request by
`app.modules.soap_notes.container.build_soap_note_facade`, bound to that
request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.soap_notes.application.services.soap_note_query_service import (
    SOAPNoteQueryService,
)
from app.modules.soap_notes.public.dto import SOAPNoteSummaryDTO
from app.modules.soap_notes.public.interfaces import SOAPNoteQueryPort


class SOAPNoteFacade(SOAPNoteQueryPort):
    def __init__(self, *, query_service: SOAPNoteQueryService) -> None:
        self._query_service = query_service

    async def soap_note_exists_for_clinical_note(self, clinical_note_id: UUID) -> bool:
        return await self._query_service.soap_note_exists_for_clinical_note(clinical_note_id)

    async def get_soap_note_summary(self, clinical_note_id: UUID) -> SOAPNoteSummaryDTO | None:
        return await self._query_service.get_soap_note_summary(clinical_note_id)
