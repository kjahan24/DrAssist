"""Module composition root.

The one place `ChiefComplaintQueryPort` gets bound to its concrete
implementation (`ChiefComplaintFacade`), and the repository interface
gets bound to its SQLAlchemy implementation. Any future module's
`api/dependencies.py` calls `build_chief_complaint_facade(session)`
rather than constructing `ChiefComplaintFacade` (or the repository)
directly.

Scope note — this task builds the Chief Complaints module's
**foundation** only: the `VisitChiefComplaint` entity, its repository,
`RecordVisitChiefComplaint` (which confirms the referenced visit exists
via the Visit module's public facade, and — when supplied — that
`recorded_by` references a doctor in the same organization, before
recording a complaint), and the public query facade. It deliberately
does **not** build any HTTP endpoint, and does not modify the
Authentication, Organization, Doctor, Patient, Visit, or Vital Signs
modules or their tables. Diagnosis, Procedures, Attachments, Clinical
Notes, SOAP Notes, Prescriptions, Lab Orders, and Billing are explicitly
out of scope for this task.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chief_complaints.application.services.chief_complaint_query_service import (
    VisitChiefComplaintQueryService,
)
from app.modules.chief_complaints.infrastructure.repositories import (
    SqlAlchemyVisitChiefComplaintRepository,
)
from app.modules.chief_complaints.public.facade import ChiefComplaintFacade


def build_chief_complaint_facade(session: AsyncSession) -> ChiefComplaintFacade:
    """Construct a `ChiefComplaintFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so they participate in the same transaction
    as the rest of that request's work.
    """
    chief_complaint_repository = SqlAlchemyVisitChiefComplaintRepository(session)

    query_service = VisitChiefComplaintQueryService(
        chief_complaint_repository=chief_complaint_repository
    )

    return ChiefComplaintFacade(query_service=query_service)
