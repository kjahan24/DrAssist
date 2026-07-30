"""`AppointmentConsistencyService` — enforces "Organization consistency"
and "Foreign keys" validation across the three cross-module references
`Appointment` carries: `patient_id`/`doctor_id` (required, at creation),
`booked_by_user_id` (optional), and `visit_id` (optional, at completion).

This is the module's "domain service" in spirit — logic that spans more
than one aggregate and isn't naturally owned by `Appointment` itself —
but it lives in the *application* layer, not `domain/`, because it
requires I/O (reading four peer modules' public ports). The domain layer
in this codebase never performs I/O (see every prior module's
`domain/entities.py`), so a literal `domain/services` package would
violate that boundary — the same reasoning
`app.modules.doctor_review.application.services
.doctor_review_consistency_service.DoctorReviewConsistencyService`
already documents for its own identically-shaped situation.

`resolve_and_validate_organization` is what makes "Patient and Doctor
must belong to the same Organization" a real runtime check rather than
an assumption: `organization_id` is not independently trusted input
anywhere in this module (see `domain/entities.py`), so this method is the
*only* place that value is ever produced.
"""

from uuid import UUID

from app.modules.appointment.domain.exceptions import (
    AppointmentVisitMismatchError,
    AppointmentVisitNotFoundError,
    BookedByUserNotFoundError,
    BookedByUserOrganizationMismatchError,
    DoctorNotFoundError,
    PatientDoctorOrganizationMismatchError,
    PatientNotFoundError,
)
from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.patient.public.interfaces import PatientQueryPort
from app.modules.visit.public.interfaces import VisitQueryPort


class AppointmentConsistencyService:
    def __init__(
        self,
        *,
        patient_query_port: PatientQueryPort,
        doctor_query_port: DoctorQueryPort,
        user_query_port: UserQueryPort,
        visit_query_port: VisitQueryPort,
    ) -> None:
        self._patients = patient_query_port
        self._doctors = doctor_query_port
        self._users = user_query_port
        self._visits = visit_query_port

    async def resolve_and_validate_organization(self, *, patient_id: UUID, doctor_id: UUID) -> UUID:
        patient_summary = await self._patients.get_patient_summary(patient_id)
        if patient_summary is None:
            raise PatientNotFoundError(patient_id)

        doctor_summary = await self._doctors.get_doctor_summary(doctor_id)
        if doctor_summary is None:
            raise DoctorNotFoundError(doctor_id)

        if patient_summary.organization_id != doctor_summary.organization_id:
            raise PatientDoctorOrganizationMismatchError(patient_id, doctor_id)

        return patient_summary.organization_id

    async def validate_booked_by_user(
        self, *, booked_by_user_id: UUID | None, organization_id: UUID
    ) -> None:
        if booked_by_user_id is None:
            return

        user_summary = await self._users.get_user_summary(booked_by_user_id)
        if user_summary is None:
            raise BookedByUserNotFoundError(booked_by_user_id)

        if user_summary.organization_id != organization_id:
            raise BookedByUserOrganizationMismatchError(booked_by_user_id, organization_id)

    async def validate_visit_for_completion(
        self,
        *,
        visit_id: UUID | None,
        organization_id: UUID,
        patient_id: UUID,
        doctor_id: UUID,
    ) -> None:
        if visit_id is None:
            return

        visit_summary = await self._visits.get_visit_summary(visit_id)
        if visit_summary is None:
            raise AppointmentVisitNotFoundError(visit_id)

        matches = (
            visit_summary.organization_id == organization_id
            and visit_summary.patient_id == patient_id
            and visit_summary.doctor_id == doctor_id
        )
        if not matches:
            raise AppointmentVisitMismatchError(visit_id)
