"""Module composition root.

The one place `ICD10CodingQueryPort` gets bound to its concrete
implementation (`ICD10CodingFacade`), and the repository interface gets
bound to its SQLAlchemy implementation. Any future module's
`api/dependencies.py` calls `build_icd10_coding_facade(session)` rather
than constructing `ICD10CodingFacade` (or the repository) directly.

Scope note — this task builds the ICD-10 Coding module's **foundation**
only: the `ICD10Coding` aggregate (one-to-*many* with `ClinicalNote` —
"One Clinical Note may contain multiple ICD-10 codes", the same shape
`DifferentialDiagnosis`/`ClinicalReasoning` already establish), its
repository, `CreateICD10Coding` (which additionally validates, when
`differential_diagnosis_id` is supplied, that the referenced record
belongs to the same clinical note, via the Differential Diagnosis
module's public facade), `UpdateICD10Coding`, `MarkICD10CodingAsPrimary`,
`UnmarkICD10CodingAsPrimary`, `MarkICD10CodingReviewed`,
`ApproveICD10Coding`, and `RejectICD10Coding` (which together derive
`organization_id`/`patient_id`/`visit_id`/`doctor_id` from the linked
clinical note, derive the starting `review_status` from `coding_source`
rather than accepting it as independent input, enforce "only one ICD-10
code can be marked as Primary", enforce "duplicate ICD-10 prevention
within a Clinical Note", and enforce "Approved and Rejected codes become
read-only"), and the public query facade. Like `DifferentialDiagnosis`
and unlike `SOAPNote`/`Prescription`/`LabOrder`, none of this module's
use cases check the parent's own editability
(`ClinicalNoteQueryPort.is_editable`/
`DifferentialDiagnosisQueryPort.is_editable`) — this task's business
rules tie read-only enforcement only to `ICD10Coding`'s own
`review_status`; see `domain/entities.py` for the full reasoning. It
deliberately does **not** build any HTTP endpoint, any AI coding, NLP,
or LLM integration (this module only *stores* ICD-10 codes assigned by
physicians or AI, never generates them), and does not modify the
Authentication, Organization, Doctor, Patient, Visit, Vital Signs, Chief
Complaints, Diagnosis, Procedures, Attachments, Clinical Notes, SOAP
Notes, Prescription, Lab Orders, Lab Results, Clinical Reasoning, or
Differential Diagnosis modules or their tables.

AI ICD Coding, SNOMED CT Mapping, DRG Coding, Billing Engine, Insurance
Claims, FHIR Condition Resource, and Medical Analytics are explicitly
out of scope for this task — they are expected to become their own
modules, each depending on `ICD10CodingQueryPort` (keyed by
`icd10_coding_id`, `clinical_note_id`, or `list_icd10_codings_for_patient`
for the patient-wide view) the same way this module itself depends on
`ClinicalNoteQueryPort`/`DifferentialDiagnosisQueryPort`.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.icd10_coding.application.services.icd10_coding_query_service import (
    ICD10CodingQueryService,
)
from app.modules.icd10_coding.infrastructure.repositories import (
    SqlAlchemyICD10CodingRepository,
)
from app.modules.icd10_coding.public.facade import ICD10CodingFacade


def build_icd10_coding_facade(session: AsyncSession) -> ICD10CodingFacade:
    """Construct an `ICD10CodingFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so it participates in the same transaction
    as the rest of that request's work.
    """
    icd10_coding_repository = SqlAlchemyICD10CodingRepository(session)

    query_service = ICD10CodingQueryService(icd10_coding_repository=icd10_coding_repository)

    return ICD10CodingFacade(query_service=query_service)
