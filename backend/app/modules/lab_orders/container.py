"""Module composition root.

The one place `LabOrderQueryPort` gets bound to its concrete
implementation (`LabOrderFacade`), and both repository interfaces get
bound to their SQLAlchemy implementations. Any future module's
`api/dependencies.py` calls `build_lab_order_facade(session)` rather than
constructing `LabOrderFacade` (or either repository) directly.

Scope note — this task builds the Lab Orders module's **foundation**
only: the `LabOrder` aggregate (which extends `ClinicalNote`, never
replacing it, and is one-to-*many* with it — "One Clinical Note may
contain multiple Lab Orders") and the separate top-level `LabOrderItem`
aggregate (one row per requested test, referencing `lab_order_id` — see
`domain/entities.py` for why it is not nested inside `LabOrder`), their
repositories, `CreateLabOrder`, `UpdateLabOrder`, `AddLabOrderItem`,
`PlaceLabOrder`, `MarkLabOrderCollected`, and `CancelLabOrder` (which
together confirm the referenced clinical note exists via the Clinical
Notes module's public facade, derive `organization_id`/`patient_id`/
`visit_id`/`doctor_id` from it, enforce "order_number is globally
unique", enforce read-only once either this lab order leaves Draft or its
clinical note is Signed/Locked, enforce "Ordered Lab Orders must contain
at least one Lab Order Item", and enforce the Draft -> Ordered ->
Collected / (Draft|Ordered) -> Cancelled status workflow), and the public
query facade. It deliberately does **not** build any HTTP endpoint, and
does not modify the Authentication, Organization, Doctor, Patient, Visit,
Vital Signs, Chief Complaints, Diagnosis, Procedures, Attachments,
Clinical Notes, SOAP Notes, or Prescription modules or their tables.

LIS, HL7/FHIR, Lab Results, AI Lab Interpretation, Clinical Decision
Support, and Notifications are explicitly out of scope for this task —
they are expected to become their own modules, each depending on
`LabOrderQueryPort` (keyed by `lab_order_id`, `clinical_note_id`, or
`list_lab_orders_for_patient` for the patient-wide view) the same way
this module itself depends on `ClinicalNoteQueryPort`.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.lab_orders.application.services.lab_order_query_service import (
    LabOrderQueryService,
)
from app.modules.lab_orders.infrastructure.repositories import (
    SqlAlchemyLabOrderItemRepository,
    SqlAlchemyLabOrderRepository,
)
from app.modules.lab_orders.public.facade import LabOrderFacade


def build_lab_order_facade(session: AsyncSession) -> LabOrderFacade:
    """Construct a `LabOrderFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so they participate in the same transaction
    as the rest of that request's work.
    """
    lab_order_repository = SqlAlchemyLabOrderRepository(session)
    lab_order_item_repository = SqlAlchemyLabOrderItemRepository(session)

    query_service = LabOrderQueryService(
        lab_order_repository=lab_order_repository,
        lab_order_item_repository=lab_order_item_repository,
    )

    return LabOrderFacade(query_service=query_service)
