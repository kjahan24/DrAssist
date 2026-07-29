"""Diagnosis module aggregate root: `VisitDiagnosis`.

A single aggregate for this foundation task. `VisitDiagnosis` is not
"owned by" the Visit module — like `VisitChiefComplaint`, it references
`Visit` (`visit_id`) and, optionally, `Doctor` (`diagnosed_by`) as peers,
each by ID only (never an object reference), validated by the
application layer via those modules' public `VisitQueryPort`/
`DoctorQueryPort` (see `application/use_cases/record_diagnosis.py`),
never by importing across `domain/` packages — see
`docs/backend-architecture/03_module_architecture.md`. Like
`VisitChiefComplaint`, this is a one-to-many relationship: one visit can
have several diagnoses, distinguished by `sequence_number`.

No value object wraps `icd10_code`: this task's business rules say only
"icd10_code is optional for now" — no format is specified (unlike
`app.modules.patient.domain.value_objects.ICD10Code`, built for
`PatientMedicalCondition` under a task that *did* specify one). Inventing
an unrequested format constraint here would be scope creep, and reusing
Patient's `ICD10Code` directly would cross the module boundary (it isn't
part of Patient's `public/` surface) — so `icd10_code` is a plain
nullable string. A future task can promote a shared value object to
`app.shared.domain.common_value_objects` if two modules ever need the
identical validated shape.

"Only one Primary diagnosis is allowed per Visit" is enforced as
*rejection* (`DuplicatePrimaryDiagnosisError`, raised by the use case
after querying sibling diagnoses), not the auto-unset pattern
`app.modules.doctor.application.use_cases.add_doctor_specialization.AddDoctorSpecialization`
uses for "one primary specialization per doctor". That pattern fits a
boolean `is_primary` flag, where "unsetting" leaves every other field
intact; `diagnosis_type` *is* the clinical classification itself, so
silently reclassifying a sibling diagnosis out from under the recording
doctor would corrupt clinical data no one asked to change — this task's
own Validation section calls it "Single Primary diagnosis validation",
which the rejection reading matches literally.

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.
`diagnosis_type` is set only at creation and has no update path in this
module — reclassifying it while preserving "one primary per visit" needs
a sibling-aware check only the application layer (with repository
access) can perform, so that capability is left for a future task rather
than half-built here.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.diagnosis.domain.enums import DiagnosisStatus, DiagnosisType
from app.modules.diagnosis.domain.events import (
    VisitDiagnosisRecorded,
    VisitDiagnosisStatusChanged,
    VisitDiagnosisUpdated,
)
from app.modules.diagnosis.domain.exceptions import (
    DiagnosisNameRequiredError,
    InvalidSequenceNumberError,
    PrimaryDiagnosisCannotBeRuledOutError,
)
from app.shared.domain.entity import AggregateRoot

_MIN_SEQUENCE_NUMBER = 1


@dataclass(kw_only=True, eq=False)
class VisitDiagnosis(AggregateRoot):
    organization_id: UUID
    visit_id: UUID
    sequence_number: int
    diagnosis_name: str
    diagnosis_type: DiagnosisType
    diagnosed_at: datetime
    icd10_code: str | None = None
    diagnosis_status: DiagnosisStatus = DiagnosisStatus.PROVISIONAL
    clinical_notes: str | None = None
    diagnosed_by: UUID | None = None

    def __post_init__(self) -> None:
        if not self.diagnosis_name or not self.diagnosis_name.strip():
            raise DiagnosisNameRequiredError()
        self.diagnosis_name = self.diagnosis_name.strip()
        _validate_sequence_number(self.sequence_number)
        _validate_primary_not_ruled_out(self.diagnosis_type, self.diagnosis_status)

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        visit_id: UUID,
        sequence_number: int,
        diagnosis_name: str,
        diagnosis_type: DiagnosisType,
        diagnosed_at: datetime,
        icd10_code: str | None = None,
        diagnosis_status: DiagnosisStatus = DiagnosisStatus.PROVISIONAL,
        clinical_notes: str | None = None,
        diagnosed_by: UUID | None = None,
    ) -> "VisitDiagnosis":
        diagnosis = cls(
            organization_id=organization_id,
            visit_id=visit_id,
            sequence_number=sequence_number,
            diagnosis_name=diagnosis_name,
            diagnosis_type=diagnosis_type,
            diagnosed_at=diagnosed_at,
            icd10_code=icd10_code,
            diagnosis_status=diagnosis_status,
            clinical_notes=clinical_notes,
            diagnosed_by=diagnosed_by,
        )
        diagnosis.record_event(
            VisitDiagnosisRecorded(
                diagnosis_id=diagnosis.id,
                organization_id=organization_id,
                visit_id=visit_id,
                sequence_number=diagnosis.sequence_number,
                diagnosis_type=diagnosis_type.value,
            )
        )
        return diagnosis

    def update_details(
        self,
        *,
        diagnosis_name: str | None = None,
        icd10_code: str | None = None,
        clinical_notes: str | None = None,
    ) -> None:
        """`sequence_number`, `diagnosis_type`, `diagnosis_status`,
        `diagnosed_by`, and `diagnosed_at` are deliberately not
        parameters here — see the module docstring for why `diagnosis_type`
        specifically has no update path yet; `diagnosis_status` changes
        only through `confirm()`/`rule_out()`, the same distinction
        `app.modules.patient.domain.entities.PatientAllergy.update_details`
        draws by excluding its own `status`."""
        if diagnosis_name is not None:
            if not diagnosis_name.strip():
                raise DiagnosisNameRequiredError()
            self.diagnosis_name = diagnosis_name.strip()
        if icd10_code is not None:
            self.icd10_code = icd10_code
        if clinical_notes is not None:
            self.clinical_notes = clinical_notes

        self.touch()
        self.record_event(VisitDiagnosisUpdated(diagnosis_id=self.id, visit_id=self.visit_id))

    def confirm(self) -> None:
        self._set_status(DiagnosisStatus.CONFIRMED)

    def rule_out(self) -> None:
        if self.diagnosis_type is DiagnosisType.PRIMARY:
            raise PrimaryDiagnosisCannotBeRuledOutError()
        self._set_status(DiagnosisStatus.RULED_OUT)

    def _set_status(self, status: DiagnosisStatus) -> None:
        if self.diagnosis_status is status:
            return
        self.diagnosis_status = status
        self.touch()
        self.record_event(
            VisitDiagnosisStatusChanged(
                diagnosis_id=self.id, visit_id=self.visit_id, status=status.value
            )
        )


def _validate_sequence_number(value: int) -> None:
    if value < _MIN_SEQUENCE_NUMBER:
        raise InvalidSequenceNumberError(value)


def _validate_primary_not_ruled_out(
    diagnosis_type: DiagnosisType, diagnosis_status: DiagnosisStatus
) -> None:
    if diagnosis_type is DiagnosisType.PRIMARY and diagnosis_status is DiagnosisStatus.RULED_OUT:
        raise PrimaryDiagnosisCannotBeRuledOutError()
