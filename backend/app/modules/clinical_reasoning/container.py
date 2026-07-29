"""Module composition root.

The one place `ClinicalReasoningQueryPort` gets bound to its concrete
implementation (`ClinicalReasoningFacade`), and the repository interface
gets bound to its SQLAlchemy implementation. Any future module's
`api/dependencies.py` calls `build_clinical_reasoning_facade(session)`
rather than constructing `ClinicalReasoningFacade` (or the repository)
directly.

Scope note — this task builds the Clinical Reasoning module's
**foundation** only: the `ClinicalReasoning` aggregate (which extends
`ClinicalNote`, never replacing it, and is one-to-*many* with it — "One
Clinical Note may contain multiple Clinical Reasoning records", the same
shape `LabOrder` already establishes), its repository,
`CreateClinicalReasoning`, `UpdateClinicalReasoning`,
`MarkClinicalReasoningReviewed`, `ApproveClinicalReasoning`, and
`RejectClinicalReasoning` (which together derive `organization_id`/
`patient_id`/`visit_id`/`doctor_id` from the linked clinical note, derive
the starting `review_status`/`reviewed_by_doctor` from `ai_generated`
rather than accepting either as independent input, and enforce
"Approved/Rejected reasoning becomes immutable"), and the public query
facade. Unlike `SOAPNote`/`Prescription`/`LabOrder`, none of this
module's use cases check the parent's own editability
(`ClinicalNoteQueryPort.is_editable`) — this task's business rules tie
read-only enforcement only to `ClinicalReasoning`'s own `review_status`;
see `domain/entities.py` for the full reasoning. It deliberately does
**not** build any HTTP endpoint, any LLM/AI-generation integration (this
module only *stores* reasoning, never produces it), and does not modify
the Authentication, Organization, Doctor, Patient, Visit, Vital Signs,
Chief Complaints, Diagnosis, Procedures, Attachments, Clinical Notes,
SOAP Notes, Prescription, Lab Orders, or Lab Results modules or their
tables.

Differential Diagnosis, ICD-10 Coding, AI Copilot, LLM Providers, Prompt
Management, Human Review Workflow, and Clinical Timeline are explicitly
out of scope for this task — they are expected to become their own
modules, each depending on `ClinicalReasoningQueryPort` (keyed by
`clinical_reasoning_id`, `clinical_note_id`, or
`list_clinical_reasoning_for_patient` for the patient-wide view) the same
way this module itself depends on `ClinicalNoteQueryPort`.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.clinical_reasoning.application.services.clinical_reasoning_query_service import (
    ClinicalReasoningQueryService,
)
from app.modules.clinical_reasoning.infrastructure.repositories import (
    SqlAlchemyClinicalReasoningRepository,
)
from app.modules.clinical_reasoning.public.facade import ClinicalReasoningFacade


def build_clinical_reasoning_facade(session: AsyncSession) -> ClinicalReasoningFacade:
    """Construct a `ClinicalReasoningFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so it participates in the same transaction
    as the rest of that request's work.
    """
    clinical_reasoning_repository = SqlAlchemyClinicalReasoningRepository(session)

    query_service = ClinicalReasoningQueryService(
        clinical_reasoning_repository=clinical_reasoning_repository
    )

    return ClinicalReasoningFacade(query_service=query_service)
