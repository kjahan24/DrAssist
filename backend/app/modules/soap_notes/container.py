"""Module composition root.

The one place `SOAPNoteQueryPort` gets bound to its concrete
implementation (`SOAPNoteFacade`), and the repository interface gets
bound to its SQLAlchemy implementation. Any future module's
`api/dependencies.py` calls `build_soap_note_facade(session)` rather
than constructing `SOAPNoteFacade` (or the repository) directly.

Scope note — this task builds the SOAP Notes module's **foundation**
only: the `SOAPNote` entity (which extends `ClinicalNote`, never
replacing it), its repository, `CreateSOAPNote` and `UpdateSOAPNote`
(which together confirm the referenced clinical note exists via the
Clinical Notes module's public facade, derive `organization_id`/
`patient_id`/`visit_id`/`doctor_id` from it, enforce "at most one SOAP
note per clinical note", and enforce read-only once that clinical note is
Signed/Locked), and the public query facade. It deliberately does **not**
build any HTTP endpoint, and does not modify the Authentication,
Organization, Doctor, Patient, Visit, Vital Signs, Chief Complaints,
Diagnosis, Procedures, or Attachments modules or their tables. It makes
two small, additive changes to the Clinical Notes module's *public port
only* (`ClinicalNoteSummaryDTO.doctor_id`, `ClinicalNoteQueryPort.
is_editable`) — see that module's own dto.py/interfaces.py docstrings for
why.

Prescription, Lab Orders, Lab Results, Clinical Reasoning, Differential
Diagnosis, ICD-10 Coding, Doctor Review, AI Copilot, and Clinical
Timeline are explicitly out of scope for this task — they are expected
to become their own modules, each depending on `SOAPNoteQueryPort` (keyed
by `clinical_note_id`) the same way this module itself depends on
`ClinicalNoteQueryPort`.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.soap_notes.application.services.soap_note_query_service import (
    SOAPNoteQueryService,
)
from app.modules.soap_notes.infrastructure.repositories import SqlAlchemySOAPNoteRepository
from app.modules.soap_notes.public.facade import SOAPNoteFacade


def build_soap_note_facade(session: AsyncSession) -> SOAPNoteFacade:
    """Construct a `SOAPNoteFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so they participate in the same transaction
    as the rest of that request's work.
    """
    soap_note_repository = SqlAlchemySOAPNoteRepository(session)

    query_service = SOAPNoteQueryService(soap_note_repository=soap_note_repository)

    return SOAPNoteFacade(query_service=query_service)
