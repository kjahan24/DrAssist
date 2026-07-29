"""`UpdateSOAPNote` — the "read-only enforcement for Signed/Locked
Clinical Notes" validation this task's own Validation section names.

`SOAPNote.update_details()` performs no status check itself (see
`domain/entities.py`), so this use case is the *only* place that
enforcement happens: `ClinicalNoteQueryPort.is_editable(clinical_note_id)`
is checked immediately before mutating, reusing the parent module's own
notion of editability rather than duplicating the Draft/In Review/
Signed/Locked logic here — the single source of truth this task's
business rules insist on ("Clinical Note status remains the source of
truth for editability"). A rejected edit raises
`app.modules.clinical_notes.domain.exceptions.ClinicalNoteNotEditableError`
directly, the same cross-module exception-reuse pattern
`create_soap_note.CreateSOAPNote` already establishes for the identical
check.
"""

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.soap_notes.application.dto import UpdateSOAPNoteInput, UpdateSOAPNoteOutput
from app.modules.soap_notes.domain.exceptions import SOAPNoteNotFoundError
from app.modules.soap_notes.domain.repositories import SOAPNoteRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UpdateSOAPNote(UseCase[UpdateSOAPNoteInput, UpdateSOAPNoteOutput]):
    def __init__(
        self,
        *,
        soap_note_repository: SOAPNoteRepository,
        clinical_note_query_port: ClinicalNoteQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._soap_notes = soap_note_repository
        self._clinical_notes = clinical_note_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: UpdateSOAPNoteInput) -> UpdateSOAPNoteOutput:
        soap_note = await self._soap_notes.get_by_id(input_dto.soap_note_id)
        if soap_note is None:
            raise SOAPNoteNotFoundError(input_dto.soap_note_id)

        if not await self._clinical_notes.is_editable(soap_note.clinical_note_id):
            raise ClinicalNoteNotEditableError()

        soap_note.update_details(
            chief_complaint=input_dto.chief_complaint,
            history_of_present_illness=input_dto.history_of_present_illness,
            review_of_systems=input_dto.review_of_systems,
            physical_examination=input_dto.physical_examination,
            vital_sign_summary=input_dto.vital_sign_summary,
            assessment=input_dto.assessment,
            plan=input_dto.plan,
        )
        await self._soap_notes.add(soap_note)
        self._uow.collect_events(soap_note.pull_events())
        await self._uow.commit()

        return UpdateSOAPNoteOutput(
            soap_note_id=soap_note.id, clinical_note_id=soap_note.clinical_note_id
        )
