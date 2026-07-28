"""Module composition root.

The one place `DoctorQueryPort` gets bound to its concrete implementation
(`DoctorFacade`), and repository interfaces get bound to their SQLAlchemy
implementations. Any future module's `api/dependencies.py` calls
`build_doctor_facade(session)` rather than constructing `DoctorFacade` (or
any repository) directly.

Scope note — this task builds the Doctor module's **foundation** only:
`Doctor`, `DoctorProfile`, `DoctorLicense`, `DoctorSpecialization`,
`DoctorSchedule` entities, repositories, `OnboardDoctor` (which
provisions a doctor and its profile atomically, consuming the
Organization and Authentication modules' public facades to confirm the
organization and user exist), `AddDoctorLicense`,
`AddDoctorSpecialization`, `AddDoctorSchedule`, and the public query
facade. It deliberately does **not** build any HTTP endpoint, and does
not modify the Authentication or Organization modules or their tables.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.doctor.application.services.doctor_query_service import DoctorQueryService
from app.modules.doctor.infrastructure.repositories import SqlAlchemyDoctorRepository
from app.modules.doctor.public.facade import DoctorFacade


def build_doctor_facade(session: AsyncSession) -> DoctorFacade:
    """Construct a `DoctorFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so they participate in the same transaction
    as the rest of that request's work.
    """
    doctor_repository = SqlAlchemyDoctorRepository(session)

    query_service = DoctorQueryService(doctor_repository=doctor_repository)

    return DoctorFacade(query_service=query_service)
