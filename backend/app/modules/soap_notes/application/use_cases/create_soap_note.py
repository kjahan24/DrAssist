"""`CreateSOAPNote` — a SOAP note always extends exactly one existing
`ClinicalNote`, and a clinical note may have at most one SOAP note.

Unlike every prior Visit sub-module use case (which resolves a peer
`Visit` and derives `organization_id` from it alone), this use case
resolves its parent through `ClinicalNoteQueryPort` and derives *all
four* identity fields — `organization_id`, `patient_id`, `visit_id`, and
`doctor_id` — from that single lookup. This is what makes "Patient,
Visit, Doctor and Organization must match the linked Clinical Note"
true unconditionally: there is no second, independently-supplied copy of
any of these fields for the derived one to disagree with. A missing
clinical note raises `ClinicalNoteNotFoundError` (defined locally — see
`domain/exceptions.py` for why).

Creation is blocked once the parent clinical note is `Signed`/`Locked`
(`ClinicalNoteQueryPort.is_editable`, reused directly from
`app.modules.clinical_notes.public.interfaces`), raising
`ClinicalNoteNotEditableError` — reused rather than wrapped, imported
from `clinical_notes.public.exceptions` (a re-export, not
`clinical_notes.domain.exceptions` directly — see
`docs/backend-architecture/10_module_communication.md`), the same
cross-module exception-reuse pattern every prior module established for
`PatientVisitNotFoundError`/`DoctorNotFoundError`. Attaching fresh,
editable SOAP content to an already-finalized note would itself be a
write the "read-only" rule is meant to prevent, even though the business
rules phrase that rule in terms of *editing* an existing SOAP note
rather than *creating* one.
"""

from app.modules.clinical_notes.public.exceptions import ClinicalNoteNotEditableError
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.soap_notes.application.dto import CreateSOAPNoteInput, CreateSOAPNoteOutput
from app.modules.soap_notes.domain.entities import SOAPNote
from app.modules.soap_notes.domain.exceptions import (
    ClinicalNoteNotFoundError,
    DuplicateSOAPNoteError,
)
from app.modules.soap_notes.domain.repositories import SOAPNoteRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateSOAPNote(UseCase[CreateSOAPNoteInput, CreateSOAPNoteOutput]):
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

    async def execute(self, input_dto: CreateSOAPNoteInput) -> CreateSOAPNoteOutput:
        clinical_note_summary = await self._clinical_notes.get_clinical_note_summary(
            input_dto.clinical_note_id
        )
        if clinical_note_summary is None:
            raise ClinicalNoteNotFoundError(input_dto.clinical_note_id)

        if not await self._clinical_notes.is_editable(input_dto.clinical_note_id):
            raise ClinicalNoteNotEditableError()

        existing = await self._soap_notes.get_by_clinical_note_id(input_dto.clinical_note_id)
        if existing is not None:
            raise DuplicateSOAPNoteError(input_dto.clinical_note_id)

        soap_note = SOAPNote.create(
            organization_id=clinical_note_summary.organization_id,
            clinical_note_id=input_dto.clinical_note_id,
            patient_id=clinical_note_summary.patient_id,
            visit_id=clinical_note_summary.visit_id,
            doctor_id=clinical_note_summary.doctor_id,
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

        return CreateSOAPNoteOutput(
            soap_note_id=soap_note.id,
            organization_id=soap_note.organization_id,
            clinical_note_id=soap_note.clinical_note_id,
        )
