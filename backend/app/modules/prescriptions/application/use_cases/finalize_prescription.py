"""`FinalizePrescription` — "A Final Prescription must contain at least
one Prescription Item", the one invariant in this module that spans two
separate aggregates (`Prescription` and `PrescriptionItem`).

Because `PrescriptionItem` is its own top-level aggregate rather than an
in-memory child of `Prescription` (see `domain/entities.py` for why), this
use case is the *only* place "at least one item" can be checked: it loads
the item list via `PrescriptionItemRepository.list_by_prescription` and
raises `PrescriptionRequiresAtLeastOneItemError` before ever calling
`Prescription.finalize()` — the same "cross-aggregate invariant belongs to
the application layer" reasoning
`app.modules.soap_notes.application.use_cases.update_soap_note
.UpdateSOAPNote` already applies to its own cross-*module* check.

Also gated by `ClinicalNoteQueryPort.is_editable` (finalizing is itself a
write) and `Prescription.ensure_editable()` (a prescription that is
already Final cannot be re-finalized).
"""

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.prescriptions.application.dto import (
    FinalizePrescriptionInput,
    FinalizePrescriptionOutput,
)
from app.modules.prescriptions.domain.exceptions import (
    PrescriptionNotFoundError,
    PrescriptionRequiresAtLeastOneItemError,
)
from app.modules.prescriptions.domain.repositories import (
    PrescriptionItemRepository,
    PrescriptionRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class FinalizePrescription(UseCase[FinalizePrescriptionInput, FinalizePrescriptionOutput]):
    def __init__(
        self,
        *,
        prescription_repository: PrescriptionRepository,
        prescription_item_repository: PrescriptionItemRepository,
        clinical_note_query_port: ClinicalNoteQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._prescriptions = prescription_repository
        self._items = prescription_item_repository
        self._clinical_notes = clinical_note_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: FinalizePrescriptionInput) -> FinalizePrescriptionOutput:
        prescription = await self._prescriptions.get_by_id(input_dto.prescription_id)
        if prescription is None:
            raise PrescriptionNotFoundError(input_dto.prescription_id)

        if not await self._clinical_notes.is_editable(prescription.clinical_note_id):
            raise ClinicalNoteNotEditableError()

        items = await self._items.list_by_prescription(prescription.id)
        if not items:
            raise PrescriptionRequiresAtLeastOneItemError(prescription.id)

        prescription.finalize()
        await self._prescriptions.add(prescription)
        self._uow.collect_events(prescription.pull_events())
        await self._uow.commit()

        return FinalizePrescriptionOutput(
            prescription_id=prescription.id,
            clinical_note_id=prescription.clinical_note_id,
            status=prescription.status,
        )
