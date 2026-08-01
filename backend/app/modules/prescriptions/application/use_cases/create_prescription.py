"""`CreatePrescription` — a prescription always extends exactly one
existing `ClinicalNote`, and a clinical note may have at most one
prescription.

Mirrors `app.modules.soap_notes.application.use_cases.create_soap_note
.CreateSOAPNote` almost exactly: resolves the parent through
`ClinicalNoteQueryPort` and derives all four identity fields —
`organization_id`, `patient_id`, `visit_id`, `doctor_id` — from that
single lookup, which is what makes "Patient, Visit, Doctor and
Organization must match the linked Clinical Note" true unconditionally.
A missing clinical note raises `ClinicalNoteNotFoundError` (defined
locally — see `domain/exceptions.py` for why).

Creation is blocked once the parent clinical note is `Signed`/`Locked`
(`ClinicalNoteQueryPort.is_editable`), raising
`ClinicalNoteNotEditableError` — reused rather than wrapped, imported
from `clinical_notes.public.exceptions` (a re-export, not
`clinical_notes.domain.exceptions` directly — see
`docs/backend-architecture/10_module_communication.md`), the same
cross-module exception-reuse pattern `CreateSOAPNote` already
established. `prescription_number` must also be globally unique, the
same treatment
`app.modules.clinical_notes.application.use_cases.create_clinical_note
.CreateClinicalNote` gives `note_number`.
"""

from app.modules.clinical_notes.public.exceptions import ClinicalNoteNotEditableError
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.prescriptions.application.dto import (
    CreatePrescriptionInput,
    CreatePrescriptionOutput,
)
from app.modules.prescriptions.domain.entities import Prescription
from app.modules.prescriptions.domain.exceptions import (
    ClinicalNoteNotFoundError,
    DuplicatePrescriptionError,
    DuplicatePrescriptionNumberError,
)
from app.modules.prescriptions.domain.repositories import PrescriptionRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreatePrescription(UseCase[CreatePrescriptionInput, CreatePrescriptionOutput]):
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

    async def execute(self, input_dto: CreatePrescriptionInput) -> CreatePrescriptionOutput:
        clinical_note_summary = await self._clinical_notes.get_clinical_note_summary(
            input_dto.clinical_note_id
        )
        if clinical_note_summary is None:
            raise ClinicalNoteNotFoundError(input_dto.clinical_note_id)

        if not await self._clinical_notes.is_editable(input_dto.clinical_note_id):
            raise ClinicalNoteNotEditableError()

        existing_for_note = await self._prescriptions.get_by_clinical_note_id(
            input_dto.clinical_note_id
        )
        if existing_for_note is not None:
            raise DuplicatePrescriptionError(input_dto.clinical_note_id)

        existing_number = await self._prescriptions.get_by_prescription_number(
            input_dto.prescription_number
        )
        if existing_number is not None:
            raise DuplicatePrescriptionNumberError(input_dto.prescription_number)

        prescription = Prescription.create(
            organization_id=clinical_note_summary.organization_id,
            clinical_note_id=input_dto.clinical_note_id,
            patient_id=clinical_note_summary.patient_id,
            visit_id=clinical_note_summary.visit_id,
            doctor_id=clinical_note_summary.doctor_id,
            prescription_number=input_dto.prescription_number,
            prescription_date=input_dto.prescription_date,
            notes=input_dto.notes,
        )
        await self._prescriptions.add(prescription)
        self._uow.collect_events(prescription.pull_events())
        await self._uow.commit()

        return CreatePrescriptionOutput(
            prescription_id=prescription.id,
            organization_id=prescription.organization_id,
            clinical_note_id=prescription.clinical_note_id,
        )
