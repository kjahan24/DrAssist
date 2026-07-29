"""Domain exceptions for the Lab Orders module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`.

`ClinicalNoteNotFoundError` is defined locally rather than reused from
`app.modules.clinical_notes.domain.exceptions` — the same situation
`app.modules.soap_notes.domain.exceptions`/
`app.modules.prescriptions.domain.exceptions` already document: the
Clinical Notes module never needed a "not found" error of its own, so
every module that *references* an existing `ClinicalNote` by id defines
this exception locally.

`ClinicalNoteNotEditableError` (the read-only enforcement error for
"if the linked Clinical Note is Signed or Locked") *is* reused directly
from `app.modules.clinical_notes.domain.exceptions` — see
`application/use_cases/create_lab_order.py`. It is distinct from
`LabOrderNotEditableError` below, which protects this module's *own*
Draft-only editability instead.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class ClinicalNoteNotFoundError(DomainError):
    def __init__(self, clinical_note_id: UUID) -> None:
        super().__init__(f"no clinical note found with id {clinical_note_id}")
        self.clinical_note_id = clinical_note_id


class LabOrderNotFoundError(DomainError):
    def __init__(self, lab_order_id: UUID) -> None:
        super().__init__(f"no lab order found with id {lab_order_id}")
        self.lab_order_id = lab_order_id


class OrderNumberRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("order_number must not be blank")


class DuplicateOrderNumberError(DomainError):
    def __init__(self, order_number: str) -> None:
        super().__init__(f"order_number {order_number!r} is already in use")
        self.order_number = order_number


class LabOrderNotEditableError(DomainError):
    def __init__(self) -> None:
        super().__init__("only a draft lab order can be modified")


class LabOrderRequiresAtLeastOneItemError(DomainError):
    def __init__(self, lab_order_id: UUID) -> None:
        super().__init__(
            f"lab order {lab_order_id} must contain at least one item before it can be ordered"
        )
        self.lab_order_id = lab_order_id


class CollectionRequiresOrderedLabOrderError(DomainError):
    def __init__(self) -> None:
        super().__init__("a lab order must be ordered before it can be marked as collected")


class LabOrderCannotBeCancelledError(DomainError):
    def __init__(self) -> None:
        super().__init__("a collected or already-cancelled lab order cannot be cancelled")


class TestNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("test_name must not be blank")
