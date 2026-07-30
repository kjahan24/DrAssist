"""Module composition root.

The one place `PatientHistoryQueryPort` gets bound to its concrete
implementation (`PatientHistoryFacade`), and the repository interface
gets bound to its SQLAlchemy implementation. Any future module's
`api/dependencies.py` calls `build_patient_history_facade(session)`
rather than constructing `PatientHistoryFacade` (or the repository)
directly.

Scope note — this task builds the Patient History module's
**foundation** only: the `PatientHistory` aggregate (an independent,
append-only ledger — *not* a duplicate of `Visit`, *not* `ClinicalNote`
itself, aggregating only *approved* clinical facts), its repository,
`CreatePatientHistory` (the module's only write operation — there is no
update, no delete, no status transition, matching "History records are
immutable" / "Patient History is append-only" literally), backed by
`PatientHistoryReferenceValidator` (dispatches on `reference_type` to
the correct one of seven peer modules' public ports to enforce
"Reference validation" / "Cross-module consistency" — read-only; this
module never writes to any other module's tables), and the public query
facade.

This module deliberately does **not** build any AI integration or any
HTTP endpoint (per this task's explicit exclusions), and does not modify
the Authentication, Organization, Doctor, Patient, Visit, Vital Signs,
Chief Complaints, Diagnosis, Procedures, Attachments, Clinical Notes,
SOAP Notes, Prescription, Lab Orders, Lab Results, Clinical Reasoning,
Differential Diagnosis, ICD-10 Coding, or Doctor Review modules or their
tables — this module only *reads* eight of them through their public
ports (via `DoctorReviewQueryPort` for the approval gate, and seven more
via `PatientHistoryReferenceValidator`). `ReferenceType` has no member
for Clinical Reasoning: it is not one of the eight artifact kinds this
schema directly references, so this module has no dependency on
`ClinicalReasoningQueryPort` — see
`application/services/patient_history_reference_validator.py`.

Timeline View, Longitudinal EMR, FHIR Bundle, FHIR Patient, FHIR
Encounter, FHIR Composition, Population Analytics, AI Medical Timeline,
Patient Portal, and Mobile App are explicitly out of scope for this
task — they are expected to become their own modules (or presentation
layers), each depending on `PatientHistoryQueryPort` (keyed by
`patient_history_id`, `(reference_type, reference_id)`, or
`list_patient_history_for_patient`/`list_patient_history_for_visit` for
the aggregate views) the same way this module itself depends on its
eight peer modules' ports. Nothing about this schema needs to change to
support them: `history_type`/`reference_type` already give a future FHIR
mapper the discriminator it needs, `encounter_date` already gives a
Timeline View its sort key, and `created_from_review` already
distinguishes review-sourced rows from any future non-review creation
path (manual chart entry, data import, Patient Portal submission)
without a schema change.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patient_history.application.services.patient_history_query_service import (
    PatientHistoryQueryService,
)
from app.modules.patient_history.infrastructure.repositories import (
    SqlAlchemyPatientHistoryRepository,
)
from app.modules.patient_history.public.facade import PatientHistoryFacade


def build_patient_history_facade(session: AsyncSession) -> PatientHistoryFacade:
    """Construct a `PatientHistoryFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so it participates in the same transaction
    as the rest of that request's work.
    """
    patient_history_repository = SqlAlchemyPatientHistoryRepository(session)

    query_service = PatientHistoryQueryService(
        patient_history_repository=patient_history_repository
    )

    return PatientHistoryFacade(query_service=query_service)
