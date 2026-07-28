"""`ScheduleVisit` — a visit always references an existing patient and an
existing doctor, and `visit_number` must be unique within the patient's
organization.

Unlike the Patient module's sub-resource use cases (which read the parent
`Patient` from a same-module repository), `PatientVisit` references
`Patient` and `Doctor` as peer modules — so both are resolved through
their public facades (`PatientQueryPort`, `DoctorQueryPort`), the same
cross-module dependency pattern
`app.modules.doctor.application.use_cases.onboard_doctor.OnboardDoctor`
established for this codebase. `organization_id` is derived from the
patient's own summary (never accepted as a separate, independently
trustable input), matching how
`app.modules.patient.application.use_cases.record_patient_allergy.RecordPatientAllergy`
et al. derive it from the loaded `Patient`. A missing patient raises
`PatientNotFoundError` directly, reused rather than wrapped (see
`docs/backend-architecture/10_module_communication.md`).

The doctor is resolved via `get_doctor_summary` (not the cheaper
`doctor_exists`) so its `organization_id` can be compared against the
patient's: a doctor belonging to a *different* organization is treated
identically to a missing one — `DoctorNotFoundError`, never a distinct
"wrong organization" error — the same cross-tenant-as-not-found pattern
`app.modules.authentication.application.use_cases.assign_role_to_user.AssignRoleToUser`
already uses for `UserNotFoundError`, so a cross-tenant reference never
leaks whether the doctor id exists at all in another organization.
"""

from app.modules.doctor.domain.exceptions import DoctorNotFoundError
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.patient.domain.exceptions import PatientNotFoundError
from app.modules.patient.public.interfaces import PatientQueryPort
from app.modules.visit.application.dto import ScheduleVisitInput, ScheduleVisitOutput
from app.modules.visit.domain.entities import PatientVisit
from app.modules.visit.domain.exceptions import DuplicateVisitNumberError
from app.modules.visit.domain.repositories import PatientVisitRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class ScheduleVisit(UseCase[ScheduleVisitInput, ScheduleVisitOutput]):
    def __init__(
        self,
        *,
        patient_visit_repository: PatientVisitRepository,
        patient_query_port: PatientQueryPort,
        doctor_query_port: DoctorQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._visits = patient_visit_repository
        self._patients = patient_query_port
        self._doctors = doctor_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: ScheduleVisitInput) -> ScheduleVisitOutput:
        patient_summary = await self._patients.get_patient_summary(input_dto.patient_id)
        if patient_summary is None:
            raise PatientNotFoundError(input_dto.patient_id)

        doctor_summary = await self._doctors.get_doctor_summary(input_dto.doctor_id)
        if (
            doctor_summary is None
            or doctor_summary.organization_id != patient_summary.organization_id
        ):
            raise DoctorNotFoundError(input_dto.doctor_id)

        existing = await self._visits.get_by_visit_number(
            organization_id=patient_summary.organization_id, visit_number=input_dto.visit_number
        )
        if existing is not None:
            raise DuplicateVisitNumberError(patient_summary.organization_id, input_dto.visit_number)

        visit = PatientVisit.create(
            organization_id=patient_summary.organization_id,
            patient_id=input_dto.patient_id,
            doctor_id=input_dto.doctor_id,
            visit_number=input_dto.visit_number,
            visit_type=input_dto.visit_type,
            visit_date=input_dto.visit_date,
            appointment_id=input_dto.appointment_id,
            priority=input_dto.priority,
            chief_complaint_summary=input_dto.chief_complaint_summary,
            reason_for_visit=input_dto.reason_for_visit,
            room_number=input_dto.room_number,
            follow_up_required=input_dto.follow_up_required,
            follow_up_date=input_dto.follow_up_date,
            notes=input_dto.notes,
        )
        await self._visits.add(visit)
        self._uow.collect_events(visit.pull_events())
        await self._uow.commit()

        return ScheduleVisitOutput(
            visit_id=visit.id,
            organization_id=visit.organization_id,
            patient_id=visit.patient_id,
            doctor_id=visit.doctor_id,
            visit_number=visit.visit_number,
            visit_status=visit.visit_status,
        )
