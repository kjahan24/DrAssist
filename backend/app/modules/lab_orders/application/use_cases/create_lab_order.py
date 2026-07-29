"""`CreateLabOrder` — a lab order always references exactly one existing
`ClinicalNote`, but unlike `SOAPNote`/`Prescription`, a clinical note may
have *many* lab orders ("One Clinical Note may contain multiple Lab
Orders") — so, unlike `CreateSOAPNote`/`CreatePrescription`, this use case
performs no "does this clinical note already have one?" check.

Otherwise mirrors `app.modules.prescriptions.application.use_cases
.create_prescription.CreatePrescription`: resolves the parent through
`ClinicalNoteQueryPort` and derives all four identity fields —
`organization_id`, `patient_id`, `visit_id`, `doctor_id` — from that
single lookup, which is what makes "Patient, Visit, Doctor and
Organization must match the linked Clinical Note" true unconditionally. A
missing clinical note raises `ClinicalNoteNotFoundError` (defined locally
— see `domain/exceptions.py` for why). Creation is blocked once the
parent clinical note is `Signed`/`Locked`
(`ClinicalNoteQueryPort.is_editable`), raising the reused
`ClinicalNoteNotEditableError`. `order_number` must be globally unique.
"""

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.lab_orders.application.dto import CreateLabOrderInput, CreateLabOrderOutput
from app.modules.lab_orders.domain.entities import LabOrder
from app.modules.lab_orders.domain.exceptions import (
    ClinicalNoteNotFoundError,
    DuplicateOrderNumberError,
)
from app.modules.lab_orders.domain.repositories import LabOrderRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateLabOrder(UseCase[CreateLabOrderInput, CreateLabOrderOutput]):
    def __init__(
        self,
        *,
        lab_order_repository: LabOrderRepository,
        clinical_note_query_port: ClinicalNoteQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._lab_orders = lab_order_repository
        self._clinical_notes = clinical_note_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: CreateLabOrderInput) -> CreateLabOrderOutput:
        clinical_note_summary = await self._clinical_notes.get_clinical_note_summary(
            input_dto.clinical_note_id
        )
        if clinical_note_summary is None:
            raise ClinicalNoteNotFoundError(input_dto.clinical_note_id)

        if not await self._clinical_notes.is_editable(input_dto.clinical_note_id):
            raise ClinicalNoteNotEditableError()

        existing_number = await self._lab_orders.get_by_order_number(input_dto.order_number)
        if existing_number is not None:
            raise DuplicateOrderNumberError(input_dto.order_number)

        lab_order = LabOrder.create(
            organization_id=clinical_note_summary.organization_id,
            clinical_note_id=input_dto.clinical_note_id,
            patient_id=clinical_note_summary.patient_id,
            visit_id=clinical_note_summary.visit_id,
            doctor_id=clinical_note_summary.doctor_id,
            order_number=input_dto.order_number,
            ordered_at=input_dto.ordered_at,
            priority=input_dto.priority,
            clinical_information=input_dto.clinical_information,
            notes=input_dto.notes,
        )
        await self._lab_orders.add(lab_order)
        self._uow.collect_events(lab_order.pull_events())
        await self._uow.commit()

        return CreateLabOrderOutput(
            lab_order_id=lab_order.id,
            organization_id=lab_order.organization_id,
            clinical_note_id=lab_order.clinical_note_id,
        )
