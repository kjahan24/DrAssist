"""Module composition root.

The one place `DifferentialDiagnosisQueryPort` gets bound to its concrete
implementation (`DifferentialDiagnosisFacade`), and the repository
interface gets bound to its SQLAlchemy implementation. Any future
module's `api/dependencies.py` calls
`build_differential_diagnosis_facade(session)` rather than constructing
`DifferentialDiagnosisFacade` (or the repository) directly.

Scope note — this task builds the Differential Diagnosis module's
**foundation** only: the `DifferentialDiagnosis` aggregate (which extends
`ClinicalNote`, never replacing it, and is one-to-*many* with it — "One
Clinical Note may have multiple Differential Diagnoses", the same shape
`ClinicalReasoning`/`LabOrder` already establish), its repository,
`CreateDifferentialDiagnosis` (which additionally validates, when
`clinical_reasoning_id` is supplied, that the referenced record belongs
to the same clinical note, via the Clinical Reasoning module's public
facade), `UpdateDifferentialDiagnosis`, `MarkDifferentialDiagnosisReviewed`,
`ApproveDifferentialDiagnosis`, and `RejectDifferentialDiagnosis` (which
together derive `organization_id`/`patient_id`/`visit_id`/`doctor_id`
from the linked clinical note, derive the starting `review_status` from
`diagnosis_source` rather than accepting it as independent input, enforce
"ranking must be unique within a Clinical Note", enforce "duplicate
diagnosis prevention", and enforce "Approved and Rejected diagnoses
become read-only"), and the public query facade. Unlike `SOAPNote`/
`Prescription`/`LabOrder`, none of this module's use cases check the
parent's own editability (`ClinicalNoteQueryPort.is_editable`/
`ClinicalReasoningQueryPort.is_editable`) — this task's business rules
tie read-only enforcement only to `DifferentialDiagnosis`'s own
`review_status`; see `domain/entities.py` for the full reasoning. It
deliberately does **not** build any HTTP endpoint, any AI inference
integration (this module only *stores* differential diagnoses, never
generates them), and does not modify the Authentication, Organization,
Doctor, Patient, Visit, Vital Signs, Chief Complaints, Diagnosis,
Procedures, Attachments, Clinical Notes, SOAP Notes, Prescription, Lab
Orders, Lab Results, or Clinical Reasoning modules or their tables.

ICD-10 Coding, SNOMED CT, AI Clinical Decision Support, Explainable AI,
Evidence-based Medicine Engine, Doctor Review Dashboard, and Clinical
Timeline are explicitly out of scope for this task — they are expected to
become their own modules, each depending on
`DifferentialDiagnosisQueryPort` (keyed by `differential_diagnosis_id`,
`clinical_note_id`, or `list_differential_diagnoses_for_patient` for the
patient-wide view) the same way this module itself depends on
`ClinicalNoteQueryPort`/`ClinicalReasoningQueryPort`.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.differential_diagnosis.application.services.differential_diagnosis_query_service import (  # noqa: E501
    DifferentialDiagnosisQueryService,
)
from app.modules.differential_diagnosis.infrastructure.repositories import (
    SqlAlchemyDifferentialDiagnosisRepository,
)
from app.modules.differential_diagnosis.public.facade import DifferentialDiagnosisFacade


def build_differential_diagnosis_facade(session: AsyncSession) -> DifferentialDiagnosisFacade:
    """Construct a `DifferentialDiagnosisFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so it participates in the same transaction
    as the rest of that request's work.
    """
    differential_diagnosis_repository = SqlAlchemyDifferentialDiagnosisRepository(session)

    query_service = DifferentialDiagnosisQueryService(
        differential_diagnosis_repository=differential_diagnosis_repository
    )

    return DifferentialDiagnosisFacade(query_service=query_service)
