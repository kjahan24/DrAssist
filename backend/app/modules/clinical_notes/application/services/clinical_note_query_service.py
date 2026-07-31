"""Read-only queries against `ClinicalNote`.

Backs the module's public `ClinicalNoteQueryPort` — the one
implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).
`list_clinical_notes_for_patient` exists specifically so a future
Clinical Timeline module can assemble a patient's full documentation
history across visits without this module needing to change — see
`app.modules.clinical_notes.container`'s scope note.

`is_editable` was added when building the SOAP Notes module: "If Clinical
Note is Signed or Locked, SOAP Note becomes read-only" needs a way for
another module to ask this *without* importing `ClinicalNoteStatus` from
`app.modules.clinical_notes.domain` — which would cross the module
boundary `docs/backend-architecture/10_module_communication.md` forbids.
This is the same "expose a boolean, not the underlying enum" shape
`app.modules.visit.public.interfaces.VisitQueryPort.is_active` and
`app.modules.doctor.public.interfaces.DoctorQueryPort.is_active` already
establish. `True` covers `Draft` and `In Review` (only `Signed`/`Locked`
block edits, per that rule); `False` for a nonexistent note, matching how
`is_active` already treats "not found" as "not usable" rather than
raising.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.clinical_notes.application.dto import ClinicalNoteSummaryDTO
from app.modules.clinical_notes.domain.entities import ClinicalNote
from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus
from app.modules.clinical_notes.domain.repositories import ClinicalNoteRepository

_NOT_EDITABLE_STATUSES = frozenset({ClinicalNoteStatus.SIGNED, ClinicalNoteStatus.LOCKED})


class ClinicalNoteQueryService:
    def __init__(self, *, clinical_note_repository: ClinicalNoteRepository) -> None:
        self._clinical_notes = clinical_note_repository

    async def clinical_note_exists(self, clinical_note_id: UUID) -> bool:
        return await self._clinical_notes.get_by_id(clinical_note_id) is not None

    async def is_editable(self, clinical_note_id: UUID) -> bool:
        note = await self._clinical_notes.get_by_id(clinical_note_id)
        return note is not None and note.status not in _NOT_EDITABLE_STATUSES

    async def get_clinical_note_summary(
        self, clinical_note_id: UUID
    ) -> ClinicalNoteSummaryDTO | None:
        note = await self._clinical_notes.get_by_id(clinical_note_id)
        return _to_summary(note) if note is not None else None

    async def list_clinical_notes_for_visit(self, visit_id: UUID) -> list[ClinicalNoteSummaryDTO]:
        notes = await self._clinical_notes.list_by_visit(visit_id)
        return [_to_summary(note) for note in notes]

    async def list_clinical_notes_for_patient(
        self, patient_id: UUID
    ) -> list[ClinicalNoteSummaryDTO]:
        notes = await self._clinical_notes.list_by_patient(patient_id)
        return [_to_summary(note) for note in notes]

    async def search_clinical_notes(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[ClinicalNoteStatus] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_id: UUID | None = None,
        encounter_from: datetime | None = None,
        encounter_to: datetime | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "encounter_datetime",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ClinicalNoteSummaryDTO], int]:
        """Search & Filtering module — see `ClinicalNoteRepository.search`'s
        docstring for filter/sort/pagination semantics."""
        notes, total = await self._clinical_notes.search(
            organization_id=organization_id,
            query=query,
            statuses=statuses,
            patient_id=patient_id,
            doctor_id=doctor_id,
            visit_id=visit_id,
            encounter_from=encounter_from,
            encounter_to=encounter_to,
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
        return [_to_summary(note) for note in notes], total


def _to_summary(note: ClinicalNote) -> ClinicalNoteSummaryDTO:
    return ClinicalNoteSummaryDTO(
        clinical_note_id=note.id,
        organization_id=note.organization_id,
        patient_id=note.patient_id,
        visit_id=note.visit_id,
        doctor_id=note.doctor_id,
        note_number=note.note_number,
        note_type=note.note_type,
        status=note.status,
        encounter_datetime=note.encounter_datetime,
        ai_generated=note.ai_generated,
        chief_complaint_summary=note.chief_complaint_summary,
        history_summary=note.history_summary,
        examination_summary=note.examination_summary,
        assessment_summary=note.assessment_summary,
        plan_summary=note.plan_summary,
        ai_model=note.ai_model,
        ai_version=note.ai_version,
        signed_at=note.signature.signed_at if note.signature is not None else None,
        signed_by=note.signature.signed_by if note.signature is not None else None,
        locked_at=note.locked_at,
    )
