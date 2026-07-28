"""`RecordVisitVitalSigns` — vital signs always reference an existing
visit, and a visit may have at most one vital signs record.

Unlike the Patient module's sub-resource use cases (which read the parent
`Patient` from a same-module repository), `VisitVitalSigns` references
`Visit` as a peer module — so it is resolved through its public facade
(`VisitQueryPort`), the same cross-module dependency pattern
`app.modules.visit.application.use_cases.schedule_visit.ScheduleVisit`
established for this codebase. `organization_id` is derived from the
visit's own summary (never accepted as a separate, independently
trustable input). A missing visit raises `PatientVisitNotFoundError`
directly, reused rather than wrapped (see
`docs/backend-architecture/10_module_communication.md`).

When `recorded_by` is provided, it is resolved via `get_doctor_summary`
(not the cheaper `doctor_exists`) so its `organization_id` can be
compared against the visit's: a doctor belonging to a *different*
organization is treated identically to a missing one —
`DoctorNotFoundError`, never a distinct "wrong organization" error — the
same cross-tenant-as-not-found pattern
`app.modules.visit.application.use_cases.schedule_visit.ScheduleVisit`
already established for its own `doctor_id`.
"""

from app.modules.doctor.domain.exceptions import DoctorNotFoundError
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.visit.domain.exceptions import PatientVisitNotFoundError
from app.modules.visit.public.interfaces import VisitQueryPort
from app.modules.vital_signs.application.dto import (
    RecordVisitVitalSignsInput,
    RecordVisitVitalSignsOutput,
)
from app.modules.vital_signs.domain.entities import VisitVitalSigns
from app.modules.vital_signs.domain.exceptions import DuplicateVitalSignsForVisitError
from app.modules.vital_signs.domain.repositories import VisitVitalSignsRepository
from app.modules.vital_signs.domain.value_objects import BloodPressure
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class RecordVisitVitalSigns(UseCase[RecordVisitVitalSignsInput, RecordVisitVitalSignsOutput]):
    def __init__(
        self,
        *,
        vital_signs_repository: VisitVitalSignsRepository,
        visit_query_port: VisitQueryPort,
        doctor_query_port: DoctorQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._vital_signs = vital_signs_repository
        self._visits = visit_query_port
        self._doctors = doctor_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: RecordVisitVitalSignsInput) -> RecordVisitVitalSignsOutput:
        visit_summary = await self._visits.get_visit_summary(input_dto.visit_id)
        if visit_summary is None:
            raise PatientVisitNotFoundError(input_dto.visit_id)

        if input_dto.recorded_by is not None:
            doctor_summary = await self._doctors.get_doctor_summary(input_dto.recorded_by)
            if (
                doctor_summary is None
                or doctor_summary.organization_id != visit_summary.organization_id
            ):
                raise DoctorNotFoundError(input_dto.recorded_by)

        existing = await self._vital_signs.get_by_visit_id(input_dto.visit_id)
        if existing is not None:
            raise DuplicateVitalSignsForVisitError(input_dto.visit_id)

        vital_signs = VisitVitalSigns.create(
            organization_id=visit_summary.organization_id,
            visit_id=input_dto.visit_id,
            temperature_c=input_dto.temperature_c,
            pulse_bpm=input_dto.pulse_bpm,
            respiratory_rate=input_dto.respiratory_rate,
            blood_pressure=BloodPressure(
                systolic=input_dto.systolic_bp, diastolic=input_dto.diastolic_bp
            ),
            spo2=input_dto.spo2,
            recorded_at=input_dto.recorded_at,
            recorded_by=input_dto.recorded_by,
            height_cm=input_dto.height_cm,
            weight_kg=input_dto.weight_kg,
            blood_glucose=input_dto.blood_glucose,
            pain_score=input_dto.pain_score,
        )
        await self._vital_signs.add(vital_signs)
        self._uow.collect_events(vital_signs.pull_events())
        await self._uow.commit()

        return RecordVisitVitalSignsOutput(
            vital_signs_id=vital_signs.id,
            organization_id=vital_signs.organization_id,
            visit_id=vital_signs.visit_id,
            bmi=vital_signs.bmi,
        )
