"""`ScheduleConsistencyService` — enforces "FK validation" and
"Organization consistency" ("Doctor and Organization must match") for
`doctor_id`.

This is the module's "domain service" in spirit — logic that isn't
naturally owned by either `DoctorSchedule` or `DoctorTimeOff` — but it
lives in the *application* layer, not `domain/`, because it requires I/O
(reading the Doctor module's public port). The domain layer in this
codebase never performs I/O (see every prior module's
`domain/entities.py`), so a literal `domain/services` package would
violate that boundary — the same reasoning
`app.modules.doctor_review.application.services
.doctor_review_consistency_service.DoctorReviewConsistencyService`
already documents for its own identically-shaped situation.

`resolve_organization_for_doctor` is what makes "Doctor and Organization
must match" true *by construction* rather than something to validate
after the fact: `organization_id` is not independently trusted input
anywhere in this module (see `domain/entities.py`), so this method is
the *only* place that value is ever produced.
"""

from uuid import UUID

from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.schedule.domain.exceptions import DoctorNotFoundError


class ScheduleConsistencyService:
    def __init__(self, *, doctor_query_port: DoctorQueryPort) -> None:
        self._doctors = doctor_query_port

    async def resolve_organization_for_doctor(self, doctor_id: UUID) -> UUID:
        doctor_summary = await self._doctors.get_doctor_summary(doctor_id)
        if doctor_summary is None:
            raise DoctorNotFoundError(doctor_id)
        return doctor_summary.organization_id
