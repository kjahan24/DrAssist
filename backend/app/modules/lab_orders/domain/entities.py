"""Lab Orders module aggregate roots: `LabOrder` and `LabOrderItem`.

`LabOrder` extends `ClinicalNote` — it does not replace it. Unlike
`SOAPNote`/`Prescription` (each a strict one-to-one child of a
`ClinicalNote`), `LabOrder` is **one-to-many**: "One Clinical Note may
contain multiple Lab Orders" — the same shape
`app.modules.clinical_notes.domain.entities.ClinicalNote` itself has
relative to `Visit` ("one visit can have several clinical notes"), one
level further down the hierarchy. `organization_id`, `patient_id`,
`visit_id`, and `doctor_id` are still not independently caller-supplied,
for the identical reason `SOAPNote`/`Prescription` already document: the
application layer derives every one of them from the referenced
`ClinicalNote`'s own summary (see
`application/use_cases/create_lab_order.py`), which is what makes
"Patient, Visit, Doctor and Organization must match the linked Clinical
Note" true unconditionally.

`LabOrderItem` is its own top-level aggregate, not a nested in-memory
child of `LabOrder` — the same "every many-per-parent entity in this
codebase is its own aggregate with its own repository" reasoning
`app.modules.prescriptions.domain.entities.PrescriptionItem` already
documents in full. "One Lab Order contains multiple Lab Order Items" is
therefore a *query* (`LabOrderItemRepository.list_by_lab_order`), not an
in-memory list on `LabOrder`. The one aggregate-spanning invariant this
task states — "Ordered Lab Orders must contain at least one Lab Order
Item" — is enforced at the application layer immediately before
`LabOrder.place_order()` is called (see
`application/use_cases/place_lab_order.py`), the same layer that already
enforces the cross-module "Clinical Note must be editable" check, for the
identical reason `Prescription.finalize()`'s own item-count check does.

`LabOrder`'s status workflow has four states, not the two-state Draft/
Final shape `Prescription` uses: `Draft -> Ordered -> Collected`, with
`Cancelled` reachable from `Draft` or `Ordered` (not from `Collected` — a
specimen already collected cannot retroactively be un-ordered). "Ordered
Lab Orders become read-only" and "Cancelled orders cannot be edited" only
name two of the four states explicitly, so — matching the conservative
"only Draft is ever named editable, so every other status defaults to not
editable" reading `app.modules.clinical_notes.domain.entities.ClinicalNote`
already establishes — `ensure_editable()` allows only `Draft`, covering
`Ordered`/`Collected`/`Cancelled` uniformly. `place_order()`,
`mark_collected()`, and `cancel()` are separate, narrowly-guarded
transition methods, not fields `update_details()` can set directly — the
same "status changes only through named transition methods, never a
generic setter" split
`app.modules.clinical_notes.domain.entities.ClinicalNote` already
establishes for its own `submit_for_review()`/`sign()`/`lock()`.
`ordered_at` is a plain required timestamp supplied at creation (like
`ClinicalNote.encounter_datetime`/`Prescription.prescription_date`), not
bound to the `Ordered` status transition — nothing in this task's business
rules ties it to that transition the way `ClinicalNote.signed_at` is tied
to `Signed`, so inventing that coupling would be scope creep.

No value object wraps any field on either entity: `order_number` has no
stated format (the same reasoning `note_number`/`prescription_number`
already document), and `test_code`/`test_name`/`specimen_type`/
`specimen_site`/`instructions` have no stated format either (the same
reasoning `app.modules.diagnosis.domain.entities` documents for
`icd10_code`).

`LabOrderItem` carries no `deleted_at` — this task's own field list gives
`LabOrder` "soft delete" but omits it for `LabOrderItem` (only
"timestamps"/"audit fields" are listed), the same asymmetry
`app.modules.prescriptions.domain.entities.PrescriptionItem` already has.
"Ownership validation" (this task's own Validation section) is satisfied
the same "true by construction" way: `LabOrderItem.lab_order_id` is only
ever set from the `LabOrder` aggregate `AddLabOrderItem` already loaded
and validated, never accepted as independent caller input.

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.lab_orders.domain.enums import LabOrderStatus, Priority
from app.modules.lab_orders.domain.events import (
    LabOrderCreated,
    LabOrderItemAdded,
    LabOrderStatusChanged,
    LabOrderUpdated,
)
from app.modules.lab_orders.domain.exceptions import (
    CollectionRequiresOrderedLabOrderError,
    LabOrderCannotBeCancelledError,
    LabOrderNotEditableError,
    OrderNumberRequiredError,
    TestNameRequiredError,
)
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class LabOrder(AggregateRoot):
    organization_id: UUID
    clinical_note_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    order_number: str
    ordered_at: datetime
    priority: Priority = Priority.ROUTINE
    status: LabOrderStatus = LabOrderStatus.DRAFT
    clinical_information: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.order_number or not self.order_number.strip():
            raise OrderNumberRequiredError()
        self.order_number = self.order_number.strip()

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        clinical_note_id: UUID,
        patient_id: UUID,
        visit_id: UUID,
        doctor_id: UUID,
        order_number: str,
        ordered_at: datetime,
        priority: Priority = Priority.ROUTINE,
        clinical_information: str | None = None,
        notes: str | None = None,
    ) -> "LabOrder":
        lab_order = cls(
            organization_id=organization_id,
            clinical_note_id=clinical_note_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
            order_number=order_number,
            ordered_at=ordered_at,
            priority=priority,
            clinical_information=clinical_information,
            notes=notes,
        )
        lab_order.record_event(
            LabOrderCreated(
                lab_order_id=lab_order.id,
                organization_id=organization_id,
                clinical_note_id=clinical_note_id,
            )
        )
        return lab_order

    def ensure_editable(self) -> None:
        """Shared by `update_details()`, `place_order()`, and the
        application-layer `AddLabOrderItem` use case: this aggregate's own
        status must be Draft. The separate cross-module check ("is the
        linked Clinical Note editable?") is not — and cannot be —
        performed here; see the module docstring."""
        if self.status is not LabOrderStatus.DRAFT:
            raise LabOrderNotEditableError()

    def update_details(
        self,
        *,
        priority: Priority | None = None,
        clinical_information: str | None = None,
        notes: str | None = None,
    ) -> None:
        """`order_number`, `ordered_at`, and every identity field are
        deliberately not parameters here — they are immutable once set,
        the same treatment
        `app.modules.clinical_notes.domain.entities.ClinicalNote` gives
        its own `note_number`."""
        self.ensure_editable()
        if priority is not None:
            self.priority = priority
        if clinical_information is not None:
            self.clinical_information = clinical_information
        if notes is not None:
            self.notes = notes

        self.touch()
        self.record_event(
            LabOrderUpdated(lab_order_id=self.id, clinical_note_id=self.clinical_note_id)
        )

    def place_order(self) -> None:
        """Whether at least one item exists is *not* checked here — that
        invariant spans two aggregates and belongs to the application
        layer; see the module docstring."""
        self.ensure_editable()
        self._set_status(LabOrderStatus.ORDERED)

    def mark_collected(self) -> None:
        if self.status is not LabOrderStatus.ORDERED:
            raise CollectionRequiresOrderedLabOrderError()
        self._set_status(LabOrderStatus.COLLECTED)

    def cancel(self) -> None:
        if self.status not in (LabOrderStatus.DRAFT, LabOrderStatus.ORDERED):
            raise LabOrderCannotBeCancelledError()
        self._set_status(LabOrderStatus.CANCELLED)

    def _set_status(self, status: LabOrderStatus) -> None:
        self.status = status
        self.touch()
        self.record_event(
            LabOrderStatusChanged(
                lab_order_id=self.id, clinical_note_id=self.clinical_note_id, status=status.value
            )
        )


@dataclass(kw_only=True, eq=False)
class LabOrderItem(AggregateRoot):
    lab_order_id: UUID
    test_code: str
    test_name: str
    specimen_type: str
    status: LabOrderStatus = LabOrderStatus.DRAFT
    specimen_site: str | None = None
    instructions: str | None = None

    def __post_init__(self) -> None:
        if not self.test_name or not self.test_name.strip():
            raise TestNameRequiredError()
        self.test_name = self.test_name.strip()

    @classmethod
    def create(
        cls,
        *,
        lab_order_id: UUID,
        test_code: str,
        test_name: str,
        specimen_type: str,
        specimen_site: str | None = None,
        instructions: str | None = None,
    ) -> "LabOrderItem":
        item = cls(
            lab_order_id=lab_order_id,
            test_code=test_code,
            test_name=test_name,
            specimen_type=specimen_type,
            specimen_site=specimen_site,
            instructions=instructions,
        )
        item.record_event(LabOrderItemAdded(lab_order_item_id=item.id, lab_order_id=lab_order_id))
        return item
