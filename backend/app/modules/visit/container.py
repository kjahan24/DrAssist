"""Module composition root.

The one place `VisitQueryPort` gets bound to its concrete implementation
(`VisitFacade`), and the repository interface gets bound to its
SQLAlchemy implementation. Any future module's `api/dependencies.py`
calls `build_visit_facade(session)` rather than constructing
`VisitFacade` (or the repository) directly.

Scope note — this task builds the Visit module's **foundation** only:
the `PatientVisit` entity, its repository, `ScheduleVisit` (which
confirms the referenced patient and doctor exist via the Patient and
Doctor modules' public facades before scheduling the visit), and the
public query facade. It deliberately does **not** build any HTTP
endpoint, and does not modify the Authentication, Organization, Doctor,
or Patient modules or their tables. Vital Signs, Diagnosis, Chief
Complaints, Procedures, Attachments, Clinical Notes, SOAP Notes,
Prescriptions, Lab Orders, and Billing are explicitly out of scope for
this task — they are expected to become their own modules, anchored on
`patient_visits` via `VisitQueryPort`.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.visit.application.services.patient_visit_query_service import (
    PatientVisitQueryService,
)
from app.modules.visit.infrastructure.repositories import SqlAlchemyPatientVisitRepository
from app.modules.visit.public.facade import VisitFacade


def build_visit_facade(session: AsyncSession) -> VisitFacade:
    """Construct a `VisitFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so they participate in the same transaction
    as the rest of that request's work.
    """
    patient_visit_repository = SqlAlchemyPatientVisitRepository(session)

    query_service = PatientVisitQueryService(patient_visit_repository=patient_visit_repository)

    return VisitFacade(query_service=query_service)
