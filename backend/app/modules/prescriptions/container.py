"""Module composition root.

The one place `PrescriptionQueryPort` gets bound to its concrete
implementation (`PrescriptionFacade`), and both repository interfaces get
bound to their SQLAlchemy implementations. Any future module's
`api/dependencies.py` calls `build_prescription_facade(session)` rather
than constructing `PrescriptionFacade` (or either repository) directly.

Scope note — this task builds the Prescription module's **foundation**
only: the `Prescription` aggregate (which extends `ClinicalNote`, never
replacing it) and the separate top-level `PrescriptionItem` aggregate
(one row per medication line, referencing `prescription_id` — see
`domain/entities.py` for why it is not nested inside `Prescription`), their
repositories, `CreatePrescription`, `UpdatePrescription`,
`AddPrescriptionItem`, and `FinalizePrescription` (which together confirm
the referenced clinical note exists via the Clinical Notes module's public
facade, derive `organization_id`/`patient_id`/`visit_id`/`doctor_id` from
it, enforce "at most one prescription per clinical note", enforce
"prescription_number is globally unique", enforce read-only once either
this prescription is Final or its clinical note is Signed/Locked, and
enforce "a Final prescription must contain at least one item"), and the
public query facade. It deliberately does **not** build any HTTP endpoint,
and does not modify the Authentication, Organization, Doctor, Patient,
Visit, Vital Signs, Chief Complaints, Diagnosis, Procedures, Attachments,
Clinical Notes, or SOAP Notes modules or their tables.

Drug Interaction Engine, Drug Allergy Checking, Medication History,
Medication Reconciliation, Pharmacy Integration, ePrescription, AI
Prescription Review, and Refill Requests are explicitly out of scope for
this task — they are expected to become their own modules, each depending
on `PrescriptionQueryPort` (keyed by `clinical_note_id`, or
`list_prescriptions_for_patient` for the patient-wide view) the same way
this module itself depends on `ClinicalNoteQueryPort`.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.prescriptions.application.services.prescription_query_service import (
    PrescriptionQueryService,
)
from app.modules.prescriptions.infrastructure.repositories import (
    SqlAlchemyPrescriptionItemRepository,
    SqlAlchemyPrescriptionRepository,
)
from app.modules.prescriptions.public.facade import PrescriptionFacade


def build_prescription_facade(session: AsyncSession) -> PrescriptionFacade:
    """Construct a `PrescriptionFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so they participate in the same transaction
    as the rest of that request's work.
    """
    prescription_repository = SqlAlchemyPrescriptionRepository(session)
    prescription_item_repository = SqlAlchemyPrescriptionItemRepository(session)

    query_service = PrescriptionQueryService(
        prescription_repository=prescription_repository,
        prescription_item_repository=prescription_item_repository,
    )

    return PrescriptionFacade(query_service=query_service)
