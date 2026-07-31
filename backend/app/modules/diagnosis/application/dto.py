"""Data Transfer Objects for the Diagnosis module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `DiagnosisSummaryDTO`
is also re-exported from `public/dto.py` for other modules to depend on.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.diagnosis.domain.enums import DiagnosisStatus, DiagnosisType

# --- RecordVisitDiagnosis -----------------------------------------------


@dataclass(frozen=True, slots=True)
class RecordVisitDiagnosisInput:
    visit_id: UUID
    sequence_number: int
    diagnosis_name: str
    diagnosis_type: DiagnosisType
    diagnosed_at: datetime
    icd10_code: str | None = None
    diagnosis_status: DiagnosisStatus = DiagnosisStatus.PROVISIONAL
    clinical_notes: str | None = None
    diagnosed_by: UUID | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordVisitDiagnosisOutput:
    diagnosis_id: UUID
    organization_id: UUID
    visit_id: UUID
    sequence_number: int
    diagnosis_type: DiagnosisType


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class DiagnosisSummaryDTO:
    diagnosis_id: UUID
    organization_id: UUID
    visit_id: UUID
    sequence_number: int
    diagnosis_name: str
    diagnosis_type: DiagnosisType
    diagnosis_status: DiagnosisStatus
    icd10_code: str | None = None
    clinical_notes: str | None = None
    diagnosed_by: UUID | None = None
    diagnosed_at: datetime | None = None

    @property
    def id(self) -> UUID:
        """Alias for `diagnosis_id` — see `AppointmentSummaryDTO.id`'s
        own docstring in `app.modules.appointment.application.dto` for
        the full reasoning (identical situation in every module)."""
        return self.diagnosis_id
