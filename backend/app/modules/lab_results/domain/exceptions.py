"""Domain exceptions for the Lab Results module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`.

`LabOrderNotFoundError` is defined locally rather than reused from
`app.modules.lab_orders.domain.exceptions` — the same situation
`app.modules.soap_notes.domain.exceptions`/
`app.modules.prescriptions.domain.exceptions` already document for
`ClinicalNoteNotFoundError`: the Lab Orders module never needed a "not
found" error of its own to expose (its own use cases raise it internally
but it isn't part of any module's `domain/exceptions.py` that's safe to
import across the boundary), so every module that *references* an
existing `LabOrder` by id defines this exception locally.

Unlike `app.modules.prescriptions.application.use_cases.create_prescription
.CreatePrescription` and `app.modules.lab_orders.application.use_cases
.create_lab_order.CreateLabOrder` (both of which reuse
`ClinicalNoteNotEditableError` because their own business rules
explicitly tie read-only enforcement to the *parent*'s status), this
module's own use cases never check `LabOrderQueryPort.is_editable` — this
task's Business Rules state only "Final Lab Results become read-only", a
self-contained rule about `LabResult`'s *own* status, never about
`LabOrder`'s. See `domain/entities.py` for the full reasoning.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class LabOrderNotFoundError(DomainError):
    def __init__(self, lab_order_id: UUID) -> None:
        super().__init__(f"no lab order found with id {lab_order_id}")
        self.lab_order_id = lab_order_id


class LabResultNotFoundError(DomainError):
    def __init__(self, lab_result_id: UUID) -> None:
        super().__init__(f"no lab result found with id {lab_result_id}")
        self.lab_result_id = lab_result_id


class DuplicateLabResultError(DomainError):
    def __init__(self, lab_order_id: UUID) -> None:
        super().__init__(f"lab order {lab_order_id} already has a lab result")
        self.lab_order_id = lab_order_id


class ResultNumberRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("result_number must not be blank")


class DuplicateResultNumberError(DomainError):
    def __init__(self, result_number: str) -> None:
        super().__init__(f"result_number {result_number!r} is already in use")
        self.result_number = result_number


class LabResultNotEditableError(DomainError):
    def __init__(self) -> None:
        super().__init__("only a draft lab result can be modified")


class LabResultRequiresAtLeastOneItemError(DomainError):
    def __init__(self, lab_result_id: UUID) -> None:
        super().__init__(
            f"lab result {lab_result_id} must contain at least one item before it can "
            "be finalized"
        )
        self.lab_result_id = lab_result_id


class TestNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("test_name must not be blank")


class InvalidLabOrderItemReferenceError(DomainError):
    def __init__(self, lab_order_item_id: UUID, lab_order_id: UUID) -> None:
        super().__init__(
            f"lab order item {lab_order_item_id} does not belong to lab order {lab_order_id}"
        )
        self.lab_order_item_id = lab_order_item_id
        self.lab_order_id = lab_order_id
