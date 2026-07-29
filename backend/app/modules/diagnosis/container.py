"""Module composition root.

The one place `DiagnosisQueryPort` gets bound to its concrete
implementation (`DiagnosisFacade`), and the repository interface gets
bound to its SQLAlchemy implementation. Any future module's
`api/dependencies.py` calls `build_diagnosis_facade(session)` rather than
constructing `DiagnosisFacade` (or the repository) directly.

Scope note — this task builds the Diagnosis module's **foundation**
only: the `VisitDiagnosis` entity, its repository,
`RecordVisitDiagnosis` (which confirms the referenced visit exists via
the Visit module's public facade, that `diagnosed_by` — when supplied —
references a doctor in the same organization, that `sequence_number` is
unique within the visit, and that at most one `Primary` diagnosis exists
per visit, before recording a diagnosis), and the public query facade.
It deliberately does **not** build any HTTP endpoint, and does not
modify the Authentication, Organization, Doctor, Patient, Visit, Vital
Signs, or Chief Complaints modules or their tables. Procedures,
Attachments, Clinical Notes, SOAP Notes, Prescriptions, Lab Orders,
Billing, and AI are explicitly out of scope for this task.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.diagnosis.application.services.diagnosis_query_service import (
    VisitDiagnosisQueryService,
)
from app.modules.diagnosis.infrastructure.repositories import SqlAlchemyVisitDiagnosisRepository
from app.modules.diagnosis.public.facade import DiagnosisFacade


def build_diagnosis_facade(session: AsyncSession) -> DiagnosisFacade:
    """Construct a `DiagnosisFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so they participate in the same transaction
    as the rest of that request's work.
    """
    diagnosis_repository = SqlAlchemyVisitDiagnosisRepository(session)

    query_service = VisitDiagnosisQueryService(diagnosis_repository=diagnosis_repository)

    return DiagnosisFacade(query_service=query_service)
