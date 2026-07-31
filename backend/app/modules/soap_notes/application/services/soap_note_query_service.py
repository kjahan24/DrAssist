"""Read-only queries against `SOAPNote`.

Backs the module's public `SOAPNoteQueryPort` — the one implementation,
per `docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.soap_notes.application.dto import SOAPNoteSummaryDTO
from app.modules.soap_notes.domain.entities import SOAPNote
from app.modules.soap_notes.domain.repositories import SOAPNoteRepository


def _to_summary(soap_note: SOAPNote) -> SOAPNoteSummaryDTO:
    return SOAPNoteSummaryDTO(
        soap_note_id=soap_note.id,
        organization_id=soap_note.organization_id,
        clinical_note_id=soap_note.clinical_note_id,
        patient_id=soap_note.patient_id,
        visit_id=soap_note.visit_id,
        doctor_id=soap_note.doctor_id,
        chief_complaint=soap_note.chief_complaint,
        history_of_present_illness=soap_note.history_of_present_illness,
        review_of_systems=soap_note.review_of_systems,
        physical_examination=soap_note.physical_examination,
        vital_sign_summary=soap_note.vital_sign_summary,
        assessment=soap_note.assessment,
        plan=soap_note.plan,
    )


class SOAPNoteQueryService:
    def __init__(self, *, soap_note_repository: SOAPNoteRepository) -> None:
        self._soap_notes = soap_note_repository

    async def soap_note_exists_for_clinical_note(self, clinical_note_id: UUID) -> bool:
        return await self._soap_notes.get_by_clinical_note_id(clinical_note_id) is not None

    async def get_soap_note_summary(self, clinical_note_id: UUID) -> SOAPNoteSummaryDTO | None:
        soap_note = await self._soap_notes.get_by_clinical_note_id(clinical_note_id)
        return _to_summary(soap_note) if soap_note is not None else None

    async def search_soap_notes(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_id: UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[SOAPNoteSummaryDTO], int]:
        """Search & Filtering module — see `SOAPNoteRepository.search`'s
        docstring for filter/sort/pagination semantics."""
        soap_notes, total = await self._soap_notes.search(
            organization_id=organization_id,
            query=query,
            patient_id=patient_id,
            doctor_id=doctor_id,
            visit_id=visit_id,
            created_from=created_from,
            created_to=created_to,
            updated_from=updated_from,
            updated_to=updated_to,
            include_deleted=include_deleted,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=offset,
            limit=limit,
        )
        return [_to_summary(soap_note) for soap_note in soap_notes], total
