"""`AddPrescriptionItem` — "One Prescription contains multiple
Prescription Items" / "Prescription Items cannot exist without a
Prescription".

`prescription_id` on the created `PrescriptionItem` is set from the
`Prescription` this use case already loaded and validated — never
accepted as independent caller input — which is what satisfies "Prescription
Item ownership validation" (this task's own Validation section) *by
construction*, the same technique `domain/entities.py` documents for the
identity FKs on `Prescription` itself.

Gated by the identical pair of checks `UpdatePrescription` uses — the
cross-module "is the linked Clinical Note editable" check and this
aggregate's own `ensure_editable()` — since adding an item is a write to
an already-existing prescription, subject to the same "Draft prescriptions
are editable / Final prescriptions become read-only" rule as any other
mutation.
"""

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.prescriptions.application.dto import (
    AddPrescriptionItemInput,
    AddPrescriptionItemOutput,
)
from app.modules.prescriptions.domain.entities import PrescriptionItem
from app.modules.prescriptions.domain.exceptions import PrescriptionNotFoundError
from app.modules.prescriptions.domain.repositories import (
    PrescriptionItemRepository,
    PrescriptionRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class AddPrescriptionItem(UseCase[AddPrescriptionItemInput, AddPrescriptionItemOutput]):
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

    async def execute(self, input_dto: AddPrescriptionItemInput) -> AddPrescriptionItemOutput:
        prescription = await self._prescriptions.get_by_id(input_dto.prescription_id)
        if prescription is None:
            raise PrescriptionNotFoundError(input_dto.prescription_id)

        prescription.ensure_editable()
        if not await self._clinical_notes.is_editable(prescription.clinical_note_id):
            raise ClinicalNoteNotEditableError()

        item = PrescriptionItem.create(
            prescription_id=prescription.id,
            medication_name=input_dto.medication_name,
            strength=input_dto.strength,
            dosage=input_dto.dosage,
            dosage_unit=input_dto.dosage_unit,
            frequency=input_dto.frequency,
            route=input_dto.route,
            duration=input_dto.duration,
            duration_unit=input_dto.duration_unit,
            quantity=input_dto.quantity,
            generic_name=input_dto.generic_name,
            instructions=input_dto.instructions,
        )
        await self._items.add(item)
        self._uow.collect_events(item.pull_events())
        await self._uow.commit()

        return AddPrescriptionItemOutput(
            prescription_item_id=item.id, prescription_id=prescription.id
        )
