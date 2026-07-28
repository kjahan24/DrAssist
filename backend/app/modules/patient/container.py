"""Module composition root.

The one place `PatientQueryPort` gets bound to its concrete
implementation (`PatientFacade`), and the repository interface gets bound
to its SQLAlchemy implementation. Any future module's `api/dependencies.py`
calls `build_patient_facade(session)` rather than constructing
`PatientFacade` (or the repository) directly.

Scope note — this task builds the Patient module's **foundation** only:
the `Patient` entity, its repository, `RegisterPatient` (which confirms
the owning organization exists via the Organization module's public
facade before registering the patient), and the public query facade. It
deliberately does **not** build any HTTP endpoint, and does not modify
the Authentication, Organization, or Doctor modules or their tables.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patient.application.services.patient_query_service import PatientQueryService
from app.modules.patient.infrastructure.repositories import SqlAlchemyPatientRepository
from app.modules.patient.public.facade import PatientFacade


def build_patient_facade(session: AsyncSession) -> PatientFacade:
    """Construct a `PatientFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so they participate in the same transaction
    as the rest of that request's work.
    """
    patient_repository = SqlAlchemyPatientRepository(session)

    query_service = PatientQueryService(patient_repository=patient_repository)

    return PatientFacade(query_service=query_service)
