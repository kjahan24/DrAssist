"""Prescription module aggregate roots: `Prescription` and
`PrescriptionItem`.

`Prescription` extends `ClinicalNote` — it does not replace it. It is a
one-to-one child of a specific `ClinicalNote` (`clinical_note_id`,
unique), the same shape `app.modules.soap_notes.domain.entities.SOAPNote`
already establishes for its own place in the Clinical Note hierarchy.
`organization_id`, `patient_id`, `visit_id`, and `doctor_id` are not
independently caller-supplied here at all — the application layer derives
every one of them from the referenced `ClinicalNote`'s own summary (see
`application/use_cases/create_prescription.py`), the same "true by
construction, not by after-the-fact validation" technique `SOAPNote`
already documents for the identical business rule ("Patient, Visit,
Doctor and Organization must match the linked Clinical Note").

`PrescriptionItem` is **not** nested inside `Prescription` as an
in-memory child collection. Every other "many rows per parent" entity in
this codebase — `VisitDiagnosis`, `VisitProcedure`, `PatientAllergy`,
`PatientMedication`, etc. — is its own top-level `AggregateRoot` with its
own repository and table, referencing its parent by id only; `Prescription`
follows that same established shape rather than inventing a novel nested-
aggregate pattern this codebase has no precedent for. "One Prescription
contains multiple Prescription Items" is therefore a *query* (see
`PrescriptionItemRepository.list_by_prescription`), not an in-memory list
on `Prescription` itself. The one truly aggregate-spanning invariant this
task states — "A Final Prescription must contain at least one Prescription
Item" — is enforced at the application layer immediately before
`Prescription.finalize()` is called (see
`application/use_cases/finalize_prescription.py`), the same layer that
already enforces the cross-module "Clinical Note must be editable" check,
since both checks equally require I/O this domain layer cannot perform.

No value object wraps any field on either entity: `strength`, `dosage`,
`dosage_unit`, `frequency`, `duration`, `duration_unit`, `quantity`, and
`instructions` have no format stated by this task's business rules — the
same reasoning `app.modules.diagnosis.domain.entities` documents for
`icd10_code`. `route` *is* a closed set of values, so it is a `StrEnum`
(`AdministrationRoute`), not a free-text field.

`PrescriptionItem` carries no `deleted_at` — this task's own field list
gives `Prescription` "soft delete" but omits it for `PrescriptionItem`,
so `PrescriptionItem` uses only `TimestampMixin`/`AuditActorMixin` at the
infrastructure layer (see `infrastructure/models.py`). "Prescription Item
ownership validation" (this task's own Validation section) is satisfied
the same "true by construction" way as the identity FKs above:
`PrescriptionItem.prescription_id` is only ever set from the `Prescription`
aggregate that `AddPrescriptionItem` already loaded and validated, never
accepted as independent caller input — see that use case.

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.modules.prescriptions.domain.enums import AdministrationRoute, PrescriptionStatus
from app.modules.prescriptions.domain.events import (
    PrescriptionCreated,
    PrescriptionFinalized,
    PrescriptionItemAdded,
    PrescriptionUpdated,
)
from app.modules.prescriptions.domain.exceptions import (
    MedicationNameRequiredError,
    PrescriptionNotEditableError,
    PrescriptionNumberRequiredError,
)
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class Prescription(AggregateRoot):
    organization_id: UUID
    clinical_note_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    prescription_number: str
    prescription_date: date
    status: PrescriptionStatus = PrescriptionStatus.DRAFT
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.prescription_number or not self.prescription_number.strip():
            raise PrescriptionNumberRequiredError()
        self.prescription_number = self.prescription_number.strip()

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        clinical_note_id: UUID,
        patient_id: UUID,
        visit_id: UUID,
        doctor_id: UUID,
        prescription_number: str,
        prescription_date: date,
        notes: str | None = None,
    ) -> "Prescription":
        prescription = cls(
            organization_id=organization_id,
            clinical_note_id=clinical_note_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
            prescription_number=prescription_number,
            prescription_date=prescription_date,
            notes=notes,
        )
        prescription.record_event(
            PrescriptionCreated(
                prescription_id=prescription.id,
                organization_id=organization_id,
                clinical_note_id=clinical_note_id,
            )
        )
        return prescription

    def ensure_editable(self) -> None:
        """The single self-check both `update_details()` and `finalize()`
        share: this aggregate's *own* status must be Draft. The separate
        cross-module check ("is the linked Clinical Note editable?") is
        not — and cannot be — performed here; see the module docstring."""
        if self.status is not PrescriptionStatus.DRAFT:
            raise PrescriptionNotEditableError()

    def update_details(
        self, *, prescription_date: date | None = None, notes: str | None = None
    ) -> None:
        """`prescription_number`, `clinical_note_id`, and every other
        identity field are deliberately not parameters here — they are
        immutable once set, the same treatment
        `app.modules.clinical_notes.domain.entities.ClinicalNote` gives
        its own `note_number`."""
        self.ensure_editable()
        if prescription_date is not None:
            self.prescription_date = prescription_date
        if notes is not None:
            self.notes = notes

        self.touch()
        self.record_event(
            PrescriptionUpdated(prescription_id=self.id, clinical_note_id=self.clinical_note_id)
        )

    def finalize(self) -> None:
        """Whether at least one item exists is *not* checked here — that
        invariant spans two aggregates and belongs to the application
        layer; see the module docstring."""
        self.ensure_editable()
        self.status = PrescriptionStatus.FINAL
        self.touch()
        self.record_event(
            PrescriptionFinalized(prescription_id=self.id, clinical_note_id=self.clinical_note_id)
        )


@dataclass(kw_only=True, eq=False)
class PrescriptionItem(AggregateRoot):
    prescription_id: UUID
    medication_name: str
    strength: str
    dosage: str
    dosage_unit: str
    frequency: str
    route: AdministrationRoute
    duration: str
    duration_unit: str
    quantity: str
    generic_name: str | None = None
    instructions: str | None = None

    def __post_init__(self) -> None:
        if not self.medication_name or not self.medication_name.strip():
            raise MedicationNameRequiredError()
        self.medication_name = self.medication_name.strip()

    @classmethod
    def create(
        cls,
        *,
        prescription_id: UUID,
        medication_name: str,
        strength: str,
        dosage: str,
        dosage_unit: str,
        frequency: str,
        route: AdministrationRoute,
        duration: str,
        duration_unit: str,
        quantity: str,
        generic_name: str | None = None,
        instructions: str | None = None,
    ) -> "PrescriptionItem":
        item = cls(
            prescription_id=prescription_id,
            medication_name=medication_name,
            strength=strength,
            dosage=dosage,
            dosage_unit=dosage_unit,
            frequency=frequency,
            route=route,
            duration=duration,
            duration_unit=duration_unit,
            quantity=quantity,
            generic_name=generic_name,
            instructions=instructions,
        )
        item.record_event(
            PrescriptionItemAdded(prescription_item_id=item.id, prescription_id=prescription_id)
        )
        return item
