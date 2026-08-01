"""`CreateClinicalNote` — a clinical note always references an existing
visit, its `patient_id` must match that visit's own patient, its
`doctor_id` (the authoring/responsible doctor — not necessarily the
visit's attending doctor) must reference an existing doctor in the same
organization, and its `note_number` must be globally unique.

`patient_id` is deliberately *not* resolved through a separate
`PatientQueryPort` call: `PatientVisit.patient_id` is already a
validated reference (no visit can exist for a nonexistent patient — see
`app.modules.visit.application.use_cases.schedule_visit.ScheduleVisit`),
so checking `visit_summary.patient_id == input_dto.patient_id` both
confirms the patient exists *and* that this visit actually belongs to
them, without a third cross-module port. A mismatch raises
`VisitPatientMismatchError` — a different failure mode from "not found",
since both the visit and the patient genuinely exist; they just don't
belong together.

Unlike the Patient module's sub-resource use cases (which read the parent
`Patient` from a same-module repository), `ClinicalNote` references
`Visit` as a peer module — so it is resolved through its public facade
(`VisitQueryPort`), the same cross-module dependency pattern
`app.modules.attachments.application.use_cases.upload_attachment.UploadVisitAttachment`
established for this codebase. `organization_id` is derived from the
visit's own summary (never accepted as a separate, independently
trustable input). A missing visit raises `PatientVisitNotFoundError`,
reused rather than wrapped, imported from `visit.public.exceptions` (a
re-export, not `visit.domain.exceptions` directly — see
`docs/backend-architecture/10_module_communication.md`, which forbids
depending on a peer module's `domain/`).

`doctor_id` is resolved via `get_doctor_summary` (not the cheaper
`doctor_exists`) so its `organization_id` can be compared against the
visit's: a doctor belonging to a *different* organization is treated
identically to a missing one — `DoctorNotFoundError`, never a distinct
"wrong organization" error — the same cross-tenant-as-not-found pattern
every prior Visit sub-module already established.
"""

from app.modules.clinical_notes.application.dto import (
    CreateClinicalNoteInput,
    CreateClinicalNoteOutput,
)
from app.modules.clinical_notes.domain.entities import ClinicalNote
from app.modules.clinical_notes.domain.exceptions import (
    DuplicateNoteNumberError,
    VisitPatientMismatchError,
)
from app.modules.clinical_notes.domain.repositories import ClinicalNoteRepository
from app.modules.doctor.public.exceptions import DoctorNotFoundError
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.visit.public.exceptions import PatientVisitNotFoundError
from app.modules.visit.public.interfaces import VisitQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateClinicalNote(UseCase[CreateClinicalNoteInput, CreateClinicalNoteOutput]):
    def __init__(
        self,
        *,
        clinical_note_repository: ClinicalNoteRepository,
        visit_query_port: VisitQueryPort,
        doctor_query_port: DoctorQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._clinical_notes = clinical_note_repository
        self._visits = visit_query_port
        self._doctors = doctor_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: CreateClinicalNoteInput) -> CreateClinicalNoteOutput:
        visit_summary = await self._visits.get_visit_summary(input_dto.visit_id)
        if visit_summary is None:
            raise PatientVisitNotFoundError(input_dto.visit_id)

        if visit_summary.patient_id != input_dto.patient_id:
            raise VisitPatientMismatchError(input_dto.visit_id, input_dto.patient_id)

        doctor_summary = await self._doctors.get_doctor_summary(input_dto.doctor_id)
        if (
            doctor_summary is None
            or doctor_summary.organization_id != visit_summary.organization_id
        ):
            raise DoctorNotFoundError(input_dto.doctor_id)

        existing = await self._clinical_notes.get_by_note_number(input_dto.note_number)
        if existing is not None:
            raise DuplicateNoteNumberError(input_dto.note_number)

        clinical_note = ClinicalNote.create(
            organization_id=visit_summary.organization_id,
            patient_id=input_dto.patient_id,
            visit_id=input_dto.visit_id,
            doctor_id=input_dto.doctor_id,
            note_number=input_dto.note_number,
            note_type=input_dto.note_type,
            encounter_datetime=input_dto.encounter_datetime,
            chief_complaint_summary=input_dto.chief_complaint_summary,
            history_summary=input_dto.history_summary,
            examination_summary=input_dto.examination_summary,
            assessment_summary=input_dto.assessment_summary,
            plan_summary=input_dto.plan_summary,
            ai_generated=input_dto.ai_generated,
            ai_model=input_dto.ai_model,
            ai_version=input_dto.ai_version,
        )
        await self._clinical_notes.add(clinical_note)
        self._uow.collect_events(clinical_note.pull_events())
        await self._uow.commit()

        return CreateClinicalNoteOutput(
            clinical_note_id=clinical_note.id,
            organization_id=clinical_note.organization_id,
            patient_id=clinical_note.patient_id,
            visit_id=clinical_note.visit_id,
            note_number=clinical_note.note_number,
            status=clinical_note.status,
        )
