"""Module composition root.

The one place `LabResultQueryPort` gets bound to its concrete
implementation (`LabResultFacade`), and both repository interfaces get
bound to their SQLAlchemy implementations. Any future module's
`api/dependencies.py` calls `build_lab_result_facade(session)` rather
than constructing `LabResultFacade` (or either repository) directly.

Scope note — this task builds the Lab Results module's **foundation**
only: the `LabResult` aggregate (which extends `LabOrder`, never
replacing it, and is strictly one-to-one with it — "One Lab Order may
have at most one Lab Result") and the separate top-level `LabResultItem`
aggregate (one row per reported test, referencing both `lab_result_id`
and `lab_order_item_id` — see `domain/entities.py` for why it is not
nested inside `LabResult`), their repositories, `CreateLabResult`,
`UpdateLabResult`, `AddLabResultItem` (which additionally validates that
`lab_order_item_id` references a real item on the parent `LabOrder`, via
`LabOrderQueryPort`), and `FinalizeLabResult` (which together derive
`organization_id`/`patient_id`/`visit_id`/`doctor_id` from the linked lab
order, enforce "result_number is globally unique", enforce read-only once
this lab result is Final, and enforce "a Final Lab Result must contain at
least one Lab Result Item"), and the public query facade. Unlike
`SOAPNote`/`Prescription`/`LabOrder`, none of this module's use cases
check the parent's own editability (`LabOrderQueryPort.is_editable`) —
this task's business rules tie read-only enforcement only to
`LabResult`'s own status; see `domain/entities.py` for the full
reasoning. It deliberately does **not** build any HTTP endpoint, and does
not modify the Authentication, Organization, Doctor, Patient, Visit,
Vital Signs, Chief Complaints, Diagnosis, Procedures, Attachments,
Clinical Notes, SOAP Notes, Prescription, or Lab Orders modules or their
tables.

AI Lab Interpretation, Clinical Reasoning, Differential Diagnosis, ICD-10
Coding, FHIR DiagnosticReport, HL7 ORU Messages, Laboratory Information
Systems (LIS), and Patient Timeline are explicitly out of scope for this
task — they are expected to become their own modules, each depending on
`LabResultQueryPort` (keyed by `lab_order_id`, or
`list_lab_results_for_patient` for the patient-wide view) the same way
this module itself depends on `LabOrderQueryPort`.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.lab_results.application.services.lab_result_query_service import (
    LabResultQueryService,
)
from app.modules.lab_results.infrastructure.repositories import (
    SqlAlchemyLabResultItemRepository,
    SqlAlchemyLabResultRepository,
)
from app.modules.lab_results.public.facade import LabResultFacade


def build_lab_result_facade(session: AsyncSession) -> LabResultFacade:
    """Construct a `LabResultFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so they participate in the same transaction
    as the rest of that request's work.
    """
    lab_result_repository = SqlAlchemyLabResultRepository(session)
    lab_result_item_repository = SqlAlchemyLabResultItemRepository(session)

    query_service = LabResultQueryService(
        lab_result_repository=lab_result_repository,
        lab_result_item_repository=lab_result_item_repository,
    )

    return LabResultFacade(query_service=query_service)
