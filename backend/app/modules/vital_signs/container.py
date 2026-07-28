"""Module composition root.

The one place `VitalSignsQueryPort` gets bound to its concrete
implementation (`VitalSignsFacade`), and the repository interface gets
bound to its SQLAlchemy implementation. Any future module's
`api/dependencies.py` calls `build_vital_signs_facade(session)` rather
than constructing `VitalSignsFacade` (or the repository) directly.

Scope note — this task builds the Vital Signs module's **foundation**
only: the `VisitVitalSigns` entity, its repository, `RecordVisitVitalSigns`
(which confirms the referenced visit exists via the Visit module's public
facade, and — when supplied — that `recorded_by` references a doctor in
the same organization, before recording vitals), and the public query
facade. It deliberately does **not** build any HTTP endpoint, and does
not modify the Authentication, Organization, Doctor, Patient, or Visit
modules or their tables. Chief Complaints, Diagnosis, Procedures,
Attachments, Clinical Notes, SOAP Notes, Prescriptions, Lab Orders, and
Billing are explicitly out of scope for this task.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vital_signs.application.services.vital_signs_query_service import (
    VisitVitalSignsQueryService,
)
from app.modules.vital_signs.infrastructure.repositories import (
    SqlAlchemyVisitVitalSignsRepository,
)
from app.modules.vital_signs.public.facade import VitalSignsFacade


def build_vital_signs_facade(session: AsyncSession) -> VitalSignsFacade:
    """Construct a `VitalSignsFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so they participate in the same transaction
    as the rest of that request's work.
    """
    vital_signs_repository = SqlAlchemyVisitVitalSignsRepository(session)

    query_service = VisitVitalSignsQueryService(vital_signs_repository=vital_signs_repository)

    return VitalSignsFacade(query_service=query_service)
