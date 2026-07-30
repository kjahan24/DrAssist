"""Module composition root.

The one place `DoctorReviewQueryPort` gets bound to its concrete
implementation (`DoctorReviewFacade`), and the repository interface gets
bound to its SQLAlchemy implementation. Any future module's
`api/dependencies.py` calls `build_doctor_review_facade(session)` rather
than constructing `DoctorReviewFacade` (or the repository) directly.

Scope note — this task builds the Doctor Review module's **foundation**
only: the `DoctorReview` aggregate (one-to-*zero-or-one* with
`ClinicalNote` — "One Clinical Note has exactly zero or one Doctor
Review", the same shape `SOAPNote`/`Prescription` already establish),
its repository, `CreateDoctorReview` (which derives
`organization_id`/`patient_id`/`visit_id`/`doctor_id` from the linked
clinical note and validates, via `DoctorReviewConsistencyService`, that
every `approved_*` category claimed `True` has a backing record in its
owning module), `UpdateDoctorReview` (same consistency re-check on the
*effective* post-update values), `ApproveDoctorReview`,
`RejectDoctorReview`, and `ReturnDoctorReviewForRevision` (which
together enforce "Review status transitions must be validated" via an
explicit transition map, and "Approved/Rejected records cannot be
edited" via `ensure_editable()`), and the public query facade.

This module represents the physician's *final review* of a clinical
encounter — a decision plus a checklist of which documentation
categories were reviewed. It is **not** authentication, authorization,
or a digital signature: no cryptographic signing, identity assertion, or
access-control decision is made here — see `domain/entities.py` for the
full reasoning on why an approval here does not cascade into mutating
`ClinicalNote`/`SOAPNote`/`Prescription`/`LabOrder`/`LabResult`/
`ClinicalReasoning`/`DifferentialDiagnosis`/`ICD10Coding`'s own records.
It deliberately does **not** build any HTTP endpoint, any AI integration,
or any Patient History/EMR aggregation view, and does not modify the
Authentication, Organization, Doctor, Patient, Visit, Vital Signs, Chief
Complaints, Diagnosis, Procedures, Attachments, Clinical Notes, SOAP
Notes, Prescription, Lab Orders, Lab Results, Clinical Reasoning,
Differential Diagnosis, or ICD-10 Coding modules or their tables — this
module only *reads* eight of them through their public ports.

Electronic Signature, Multi-stage Approval, Quality Assurance Review,
Clinical Audit, FHIR Provenance, FHIR Composition, AI Clinical Copilot,
Medical Legal Audit, and Hospital Review Committee are explicitly out of
scope for this task — they are expected to become their own modules (or
extensions of this one), each depending on `DoctorReviewQueryPort`
(keyed by `doctor_review_id`, `clinical_note_id`, or
`list_doctor_reviews_for_patient` for the patient-wide view) the same
way this module itself depends on its eight peer modules' ports. Nothing
about this schema needs to change to support them: `reviewed_at` and the
`review_status` transition map already give a signature/multi-stage
workflow a timestamp and a validated state machine to extend.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.doctor_review.application.services.doctor_review_query_service import (
    DoctorReviewQueryService,
)
from app.modules.doctor_review.infrastructure.repositories import (
    SqlAlchemyDoctorReviewRepository,
)
from app.modules.doctor_review.public.facade import DoctorReviewFacade


def build_doctor_review_facade(session: AsyncSession) -> DoctorReviewFacade:
    """Construct a `DoctorReviewFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so it participates in the same transaction
    as the rest of that request's work.
    """
    doctor_review_repository = SqlAlchemyDoctorReviewRepository(session)

    query_service = DoctorReviewQueryService(doctor_review_repository=doctor_review_repository)

    return DoctorReviewFacade(query_service=query_service)
