"""Lab Results module aggregate roots: `LabResult` and `LabResultItem`.

`LabResult` extends `LabOrder` — it does not replace it, and unlike every
prior child-document module in this session (`SOAPNote`/`Prescription`
extend `ClinicalNote`; `LabOrder` itself extends `ClinicalNote`),
`LabResult`'s parent is `LabOrder`, one level further down the hierarchy.
It is a strict one-to-one child ("One Lab Order may have at most one Lab
Result" — the same shape `SOAPNote`/`Prescription` already establish for
their own place under `ClinicalNote`). `organization_id`, `patient_id`,
`visit_id`, and `doctor_id` are still not independently caller-supplied:
the application layer derives every one of them from the referenced
`LabOrder`'s own summary, obtained via `LabOrderQueryPort` (see
`application/use_cases/create_lab_result.py`) — the identical "true by
construction" technique every prior child-document module uses, here
applied one level deeper.

**This module's read-only rule is narrower than every prior child-
document module's.** `SOAPNote`, `Prescription`, and `LabOrder` each also
check their *parent*'s editability (`ClinicalNoteQueryPort.is_editable`)
before allowing a write, because their own task's business rules
explicitly said so ("If the linked Clinical Note is Signed or Locked, ...
becomes read-only"). This task's Business Rules say only "Final Lab
Results become read-only" — a rule entirely about `LabResult`'s *own*
status, never about `LabOrder`'s. Extending that check to also gate on
`LabOrderQueryPort.is_editable` would be inventing a business rule this
task never states (`LabOrder.is_editable` is actually `False` for
`Ordered`/`Collected` — exactly the states a real lab result would be
attached *during* — so reusing it here would be actively wrong, not just
unrequested). `ensure_editable()` therefore checks only this aggregate's
own `status`, with no cross-module port call anywhere in this module's
use cases.

`LabResultItem` is its own top-level aggregate, not a nested in-memory
child of `LabResult` — the same "every many-per-parent entity in this
codebase is its own aggregate with its own repository" reasoning
`app.modules.prescriptions.domain.entities.PrescriptionItem` and
`app.modules.lab_orders.domain.entities.LabOrderItem` already document in
full. "One Lab Result contains multiple Lab Result Items" is therefore a
*query* (`LabResultItemRepository.list_by_lab_result`), not an in-memory
list. The one aggregate-spanning invariant this task states — "A Final
Lab Result must contain at least one Lab Result Item" — is enforced at
the application layer immediately before `LabResult.finalize()` is called
(see `application/use_cases/finalize_lab_result.py`), the identical
reasoning `Prescription.finalize()`'s own item-count check already
documents.

"Every Lab Result Item must reference an existing Lab Order Item" is a
*second* cross-aggregate (in fact cross-module) invariant this task
states, unique to this module: `LabResultItem.lab_order_item_id` names a
row that must exist among the *parent `LabOrder`*'s own items. This
cannot be validated here either — it requires `LabOrderQueryPort` — so it
too is checked at the application layer, in
`application/use_cases/add_lab_result_item.py`.

No value object wraps any field on either entity: `result_number` has no
stated format (the same reasoning `order_number`/`prescription_number`
already document), and `test_code`/`test_name`/`result_value`/
`result_unit`/`reference_range`/`interpretation`/`laboratory_name`/
`comments` have no stated format either (the same reasoning
`app.modules.diagnosis.domain.entities` documents for `icd10_code`).
`abnormal_flag` *is* a closed set of values, so it is a `StrEnum`
(`AbnormalFlag`), not a free-text field.

`LabResultItem` carries no `deleted_at` — this task's own field list
gives `LabResult` "soft delete" but omits it for `LabResultItem` (only
"timestamps"/"audit fields" are listed), the same asymmetry
`PrescriptionItem`/`LabOrderItem` already have. "Ownership validation"
(this task's own Validation section) is satisfied the same "true by
construction" way: `LabResultItem.lab_result_id` is only ever set from
the `LabResult` aggregate `AddLabResultItem` already loaded and
validated, never accepted as independent caller input.

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.lab_results.domain.enums import AbnormalFlag, LabResultStatus
from app.modules.lab_results.domain.events import (
    LabResultCreated,
    LabResultFinalized,
    LabResultItemAdded,
    LabResultUpdated,
)
from app.modules.lab_results.domain.exceptions import (
    LabResultNotEditableError,
    ResultNumberRequiredError,
    TestNameRequiredError,
)
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class LabResult(AggregateRoot):
    organization_id: UUID
    lab_order_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    result_number: str
    reported_at: datetime
    status: LabResultStatus = LabResultStatus.DRAFT
    laboratory_name: str | None = None
    comments: str | None = None

    def __post_init__(self) -> None:
        if not self.result_number or not self.result_number.strip():
            raise ResultNumberRequiredError()
        self.result_number = self.result_number.strip()

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        lab_order_id: UUID,
        patient_id: UUID,
        visit_id: UUID,
        doctor_id: UUID,
        result_number: str,
        reported_at: datetime,
        laboratory_name: str | None = None,
        comments: str | None = None,
    ) -> "LabResult":
        lab_result = cls(
            organization_id=organization_id,
            lab_order_id=lab_order_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
            result_number=result_number,
            reported_at=reported_at,
            laboratory_name=laboratory_name,
            comments=comments,
        )
        lab_result.record_event(
            LabResultCreated(
                lab_result_id=lab_result.id,
                organization_id=organization_id,
                lab_order_id=lab_order_id,
            )
        )
        return lab_result

    def ensure_editable(self) -> None:
        """Shared by `update_details()`, `finalize()`, and the
        application-layer `AddLabResultItem` use case: this aggregate's
        own status must be Draft. Unlike every prior child-document
        module, there is no separate cross-module check here — see the
        module docstring for why."""
        if self.status is not LabResultStatus.DRAFT:
            raise LabResultNotEditableError()

    def update_details(
        self, *, laboratory_name: str | None = None, comments: str | None = None
    ) -> None:
        """`result_number`, `reported_at`, and every identity field are
        deliberately not parameters here — they are immutable once set,
        the same treatment
        `app.modules.clinical_notes.domain.entities.ClinicalNote` gives
        its own `note_number`."""
        self.ensure_editable()
        if laboratory_name is not None:
            self.laboratory_name = laboratory_name
        if comments is not None:
            self.comments = comments

        self.touch()
        self.record_event(LabResultUpdated(lab_result_id=self.id, lab_order_id=self.lab_order_id))

    def finalize(self) -> None:
        """Whether at least one item exists is *not* checked here — that
        invariant spans two aggregates and belongs to the application
        layer; see the module docstring."""
        self.ensure_editable()
        self.status = LabResultStatus.FINAL
        self.touch()
        self.record_event(LabResultFinalized(lab_result_id=self.id, lab_order_id=self.lab_order_id))


@dataclass(kw_only=True, eq=False)
class LabResultItem(AggregateRoot):
    lab_result_id: UUID
    lab_order_item_id: UUID
    test_code: str
    test_name: str
    result_value: str
    abnormal_flag: AbnormalFlag
    result_unit: str | None = None
    reference_range: str | None = None
    interpretation: str | None = None

    def __post_init__(self) -> None:
        if not self.test_name or not self.test_name.strip():
            raise TestNameRequiredError()
        self.test_name = self.test_name.strip()

    @classmethod
    def create(
        cls,
        *,
        lab_result_id: UUID,
        lab_order_item_id: UUID,
        test_code: str,
        test_name: str,
        result_value: str,
        abnormal_flag: AbnormalFlag,
        result_unit: str | None = None,
        reference_range: str | None = None,
        interpretation: str | None = None,
    ) -> "LabResultItem":
        item = cls(
            lab_result_id=lab_result_id,
            lab_order_item_id=lab_order_item_id,
            test_code=test_code,
            test_name=test_name,
            result_value=result_value,
            abnormal_flag=abnormal_flag,
            result_unit=result_unit,
            reference_range=reference_range,
            interpretation=interpretation,
        )
        item.record_event(
            LabResultItemAdded(lab_result_item_id=item.id, lab_result_id=lab_result_id)
        )
        return item
