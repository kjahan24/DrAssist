"""`NotificationConsistencyService` — makes "every notification belongs to
one organization" true by construction and "recipient existence" a real
runtime check: `organization_id` is never independently caller-supplied
anywhere in this module (see `domain/entities.py`), so
`resolve_organization_for_recipient` is the *only* place that value is
ever produced — the same single-parent-derivation technique
`app.modules.schedule.application.services.schedule_consistency_service
.ScheduleConsistencyService` already establishes for its own `doctor_id`
-> `organization_id` derivation.

This is the module's "domain service" in spirit — logic that spans more
than one aggregate and isn't naturally owned by `Notification` itself —
but it lives in the *application* layer, not `domain/`, because it
requires I/O (reading the Authentication module's public port). The
domain layer in this codebase never performs I/O (see every prior
module's `domain/entities.py`), so a literal `domain/services` package
would violate that boundary — the same reasoning
`app.modules.appointment.application.services
.appointment_consistency_service.AppointmentConsistencyService` already
documents for its own identically-shaped situation.

This service intentionally does **not** validate `reference_type`/
`reference_id` against Organization, Doctor, Patient, Appointment,
Schedule, or Visit — see `domain/entities.py` for why that field is a
free-form, non-existence-checked discriminator rather than a closed
enum.
"""

from uuid import UUID

from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.notification.domain.exceptions import RecipientNotFoundError


class NotificationConsistencyService:
    def __init__(self, *, user_query_port: UserQueryPort) -> None:
        self._users = user_query_port

    async def resolve_organization_for_recipient(self, recipient_user_id: UUID) -> UUID:
        user_summary = await self._users.get_user_summary(recipient_user_id)
        if user_summary is None:
            raise RecipientNotFoundError(recipient_user_id)
        return user_summary.organization_id
