"""Read-only queries against `Prescription`/`PrescriptionItem`.

Backs the module's public `PrescriptionQueryPort` — the one
implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

Depends on both repositories (unlike most other query services in this
codebase, which depend on exactly one) because `PrescriptionSummaryDTO`
is deliberately *not* narrow — it embeds the full item list, since this
task's own Future Compatibility list (Drug Interaction Engine, Drug
Allergy Checking, Medication History, Medication Reconciliation, Pharmacy
Integration, ePrescription, AI Prescription Review, Refill Requests) is a
list of features that all need the actual medication data, not just
"a prescription exists" — the same "don't build a narrow DTO a real
future consumer would immediately need to re-query" reasoning
`app.modules.soap_notes.application.dto` documents for
`SOAPNoteSummaryDTO`.

`list_prescriptions_for_patient` exists for the same reason
`app.modules.clinical_notes.application.services.clinical_note_query_service
.ClinicalNoteQueryService.list_clinical_notes_for_patient` does: so a
future Medication History module can assemble a patient's full
prescribing history across visits without this module needing to change.
"""

from uuid import UUID

from app.modules.prescriptions.application.dto import (
    PrescriptionItemSummaryDTO,
    PrescriptionSummaryDTO,
)
from app.modules.prescriptions.domain.entities import Prescription, PrescriptionItem
from app.modules.prescriptions.domain.repositories import (
    PrescriptionItemRepository,
    PrescriptionRepository,
)


class PrescriptionQueryService:
    def __init__(
        self,
        *,
        prescription_repository: PrescriptionRepository,
        prescription_item_repository: PrescriptionItemRepository,
    ) -> None:
        self._prescriptions = prescription_repository
        self._items = prescription_item_repository

    async def prescription_exists_for_clinical_note(self, clinical_note_id: UUID) -> bool:
        return await self._prescriptions.get_by_clinical_note_id(clinical_note_id) is not None

    async def get_prescription_summary(
        self, clinical_note_id: UUID
    ) -> PrescriptionSummaryDTO | None:
        prescription = await self._prescriptions.get_by_clinical_note_id(clinical_note_id)
        if prescription is None:
            return None
        return await self._to_summary(prescription)

    async def get_prescription_summary_by_id(
        self, prescription_id: UUID
    ) -> PrescriptionSummaryDTO | None:
        """By the prescription's own id — added by the REST APIs task so
        `AddPrescriptionItem` (whose output only carries `prescription_id`,
        not `clinical_note_id`) has a way to refetch the full summary
        after adding an item, without a second round-trip through
        `get_by_clinical_note_id`."""
        prescription = await self._prescriptions.get_by_id(prescription_id)
        if prescription is None:
            return None
        return await self._to_summary(prescription)

    async def list_prescriptions_for_patient(
        self, patient_id: UUID
    ) -> list[PrescriptionSummaryDTO]:
        prescriptions = await self._prescriptions.list_by_patient(patient_id)
        return [await self._to_summary(prescription) for prescription in prescriptions]

    async def _to_summary(self, prescription: Prescription) -> PrescriptionSummaryDTO:
        items = await self._items.list_by_prescription(prescription.id)
        return PrescriptionSummaryDTO(
            prescription_id=prescription.id,
            organization_id=prescription.organization_id,
            clinical_note_id=prescription.clinical_note_id,
            patient_id=prescription.patient_id,
            visit_id=prescription.visit_id,
            doctor_id=prescription.doctor_id,
            prescription_number=prescription.prescription_number,
            prescription_date=prescription.prescription_date,
            status=prescription.status,
            notes=prescription.notes,
            items=[_to_item_summary(item) for item in items],
        )


def _to_item_summary(item: PrescriptionItem) -> PrescriptionItemSummaryDTO:
    return PrescriptionItemSummaryDTO(
        prescription_item_id=item.id,
        prescription_id=item.prescription_id,
        medication_name=item.medication_name,
        strength=item.strength,
        dosage=item.dosage,
        dosage_unit=item.dosage_unit,
        frequency=item.frequency,
        route=item.route,
        duration=item.duration,
        duration_unit=item.duration_unit,
        quantity=item.quantity,
        generic_name=item.generic_name,
        instructions=item.instructions,
    )
