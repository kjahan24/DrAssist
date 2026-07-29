"""`RecordVisitDiagnosis` — a diagnosis always references an existing
visit, its `sequence_number` must be unique within that visit, and at
most one `Primary` diagnosis may exist per visit.

Unlike the Patient module's sub-resource use cases (which read the parent
`Patient` from a same-module repository), `VisitDiagnosis` references
`Visit` as a peer module — so it is resolved through its public facade
(`VisitQueryPort`), the same cross-module dependency pattern
`app.modules.chief_complaints.application.use_cases.record_chief_complaint.RecordVisitChiefComplaint`
established for this codebase. `organization_id` is derived from the
visit's own summary (never accepted as a separate, independently
trustable input). A missing visit raises `PatientVisitNotFoundError`
directly, reused rather than wrapped (see
`docs/backend-architecture/10_module_communication.md`).

When `diagnosed_by` is provided, it is resolved via `get_doctor_summary`
(not the cheaper `doctor_exists`) so its `organization_id` can be
compared against the visit's: a doctor belonging to a *different*
organization is treated identically to a missing one —
`DoctorNotFoundError`, never a distinct "wrong organization" error — the
same cross-tenant-as-not-found pattern `RecordVisitVitalSigns`/
`RecordVisitChiefComplaint` already established.

"Only one Primary diagnosis per visit" is checked here (via
`get_primary_for_visit`), not inside the entity — see
`app.modules.diagnosis.domain.entities` for why this is a rejection
rather than the "unset the previous primary" pattern used elsewhere in
this codebase.
"""

from app.modules.diagnosis.application.dto import (
    RecordVisitDiagnosisInput,
    RecordVisitDiagnosisOutput,
)
from app.modules.diagnosis.domain.entities import VisitDiagnosis
from app.modules.diagnosis.domain.enums import DiagnosisType
from app.modules.diagnosis.domain.exceptions import (
    DuplicatePrimaryDiagnosisError,
    DuplicateSequenceNumberError,
)
from app.modules.diagnosis.domain.repositories import VisitDiagnosisRepository
from app.modules.doctor.domain.exceptions import DoctorNotFoundError
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.visit.domain.exceptions import PatientVisitNotFoundError
from app.modules.visit.public.interfaces import VisitQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class RecordVisitDiagnosis(UseCase[RecordVisitDiagnosisInput, RecordVisitDiagnosisOutput]):
    def __init__(
        self,
        *,
        diagnosis_repository: VisitDiagnosisRepository,
        visit_query_port: VisitQueryPort,
        doctor_query_port: DoctorQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._diagnoses = diagnosis_repository
        self._visits = visit_query_port
        self._doctors = doctor_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: RecordVisitDiagnosisInput) -> RecordVisitDiagnosisOutput:
        visit_summary = await self._visits.get_visit_summary(input_dto.visit_id)
        if visit_summary is None:
            raise PatientVisitNotFoundError(input_dto.visit_id)

        if input_dto.diagnosed_by is not None:
            doctor_summary = await self._doctors.get_doctor_summary(input_dto.diagnosed_by)
            if (
                doctor_summary is None
                or doctor_summary.organization_id != visit_summary.organization_id
            ):
                raise DoctorNotFoundError(input_dto.diagnosed_by)

        existing_sequence = await self._diagnoses.get_by_visit_and_sequence(
            visit_id=input_dto.visit_id, sequence_number=input_dto.sequence_number
        )
        if existing_sequence is not None:
            raise DuplicateSequenceNumberError(input_dto.visit_id, input_dto.sequence_number)

        if input_dto.diagnosis_type is DiagnosisType.PRIMARY:
            existing_primary = await self._diagnoses.get_primary_for_visit(input_dto.visit_id)
            if existing_primary is not None:
                raise DuplicatePrimaryDiagnosisError(input_dto.visit_id)

        diagnosis = VisitDiagnosis.create(
            organization_id=visit_summary.organization_id,
            visit_id=input_dto.visit_id,
            sequence_number=input_dto.sequence_number,
            diagnosis_name=input_dto.diagnosis_name,
            diagnosis_type=input_dto.diagnosis_type,
            diagnosed_at=input_dto.diagnosed_at,
            icd10_code=input_dto.icd10_code,
            diagnosis_status=input_dto.diagnosis_status,
            clinical_notes=input_dto.clinical_notes,
            diagnosed_by=input_dto.diagnosed_by,
        )
        await self._diagnoses.add(diagnosis)
        self._uow.collect_events(diagnosis.pull_events())
        await self._uow.commit()

        return RecordVisitDiagnosisOutput(
            diagnosis_id=diagnosis.id,
            organization_id=diagnosis.organization_id,
            visit_id=diagnosis.visit_id,
            sequence_number=diagnosis.sequence_number,
            diagnosis_type=diagnosis.diagnosis_type,
        )
