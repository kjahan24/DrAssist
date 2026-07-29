"""`UpdatePrescription` — the "read-only enforcement" and "Draft
prescriptions are editable" / "Final prescriptions become read-only"
validation this task's own Business Rules and Validation sections name.

Two independent checks gate every update, mirroring
`app.modules.soap_notes.application.use_cases.update_soap_note
.UpdateSOAPNote` exactly: `ClinicalNoteQueryPort.is_editable` (the
cross-module "is the linked Clinical Note itself Signed/Locked" check —
raises the reused `ClinicalNoteNotEditableError`) and
`Prescription.ensure_editable()` (this aggregate's own Draft/Final
self-check, called internally by `update_details()` — raises
`PrescriptionNotEditableError`). Only `prescription_date`/`notes` are
mutable here; `prescription_number` and every identity field are
immutable once set — see `domain/entities.py`.
"""

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.prescriptions.application.dto import (
    UpdatePrescriptionInput,
    UpdatePrescriptionOutput,
)
from app.modules.prescriptions.domain.exceptions import PrescriptionNotFoundError
from app.modules.prescriptions.domain.repositories import PrescriptionRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UpdatePrescription(UseCase[UpdatePrescriptionInput, UpdatePrescriptionOutput]):
    def __init__(
        self,
        *,
        prescription_repository: PrescriptionRepository,
        clinical_note_query_port: ClinicalNoteQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._prescriptions = prescription_repository
        self._clinical_notes = clinical_note_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: UpdatePrescriptionInput) -> UpdatePrescriptionOutput:
        prescription = await self._prescriptions.get_by_id(input_dto.prescription_id)
        if prescription is None:
            raise PrescriptionNotFoundError(input_dto.prescription_id)

        if not await self._clinical_notes.is_editable(prescription.clinical_note_id):
            raise ClinicalNoteNotEditableError()

        prescription.update_details(
            prescription_date=input_dto.prescription_date, notes=input_dto.notes
        )
        await self._prescriptions.add(prescription)
        self._uow.collect_events(prescription.pull_events())
        await self._uow.commit()

        return UpdatePrescriptionOutput(
            prescription_id=prescription.id, clinical_note_id=prescription.clinical_note_id
        )
