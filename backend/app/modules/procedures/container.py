"""Module composition root.

The one place `ProcedureQueryPort` gets bound to its concrete
implementation (`ProcedureFacade`), and the repository interface gets
bound to its SQLAlchemy implementation. Any future module's
`api/dependencies.py` calls `build_procedure_facade(session)` rather than
constructing `ProcedureFacade` (or the repository) directly.

Scope note — this task builds the Procedures module's **foundation**
only: the `VisitProcedure` entity, its repository, `RecordVisitProcedure`
(which confirms the referenced visit exists via the Visit module's
public facade, that `performed_by` — when supplied — references a
doctor in the same organization, and that `sequence_number` is unique
within the visit, before recording a procedure), and the public query
facade. It deliberately does **not** build any HTTP endpoint, and does
not modify the Authentication, Organization, Doctor, Patient, Visit,
Vital Signs, Chief Complaints, or Diagnosis modules or their tables.
Attachments, Clinical Notes, SOAP Notes, Prescriptions, Lab Orders,
Billing, and AI are explicitly out of scope for this task.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.procedures.application.services.procedure_query_service import (
    VisitProcedureQueryService,
)
from app.modules.procedures.infrastructure.repositories import SqlAlchemyVisitProcedureRepository
from app.modules.procedures.public.facade import ProcedureFacade


def build_procedure_facade(session: AsyncSession) -> ProcedureFacade:
    """Construct a `ProcedureFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so they participate in the same transaction
    as the rest of that request's work.
    """
    procedure_repository = SqlAlchemyVisitProcedureRepository(session)

    query_service = VisitProcedureQueryService(procedure_repository=procedure_repository)

    return ProcedureFacade(query_service=query_service)
