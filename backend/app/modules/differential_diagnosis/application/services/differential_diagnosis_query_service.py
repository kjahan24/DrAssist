"""Read-only queries against `DifferentialDiagnosis`.

Backs the module's public `DifferentialDiagnosisQueryPort` — the one
implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

Shaped like `app.modules.clinical_reasoning.application.services
.clinical_reasoning_query_service.ClinicalReasoningQueryService`:
`DifferentialDiagnosis` is one-to-*many* with `ClinicalNote` ("One
Clinical Note may have multiple Differential Diagnoses"), so
`list_differential_diagnoses_for_clinical_note` — not a single
`get_..._summary(clinical_note_id)` — is the query keyed by the parent;
`get_differential_diagnosis_summary` is instead keyed by this
aggregate's own id. `is_editable` mirrors the same boolean-not-enum
shape, for the identical reason: a future module (Doctor Review
Dashboard, AI Clinical Decision Support, in particular) needs to ask
"can this diagnosis still be modified?" without importing `ReviewStatus`
across the module boundary. `list_differential_diagnoses_for_patient`
exists for the same reason
`app.modules.clinical_notes.application.services.clinical_note_query_service
.ClinicalNoteQueryService.list_clinical_notes_for_patient` does: so a
future Clinical Timeline module can assemble a patient's full
differential-diagnosis history across clinical notes without this module
needing to change.
"""

from uuid import UUID

from app.modules.differential_diagnosis.application.dto import (
    DifferentialDiagnosisSummaryDTO,
)
from app.modules.differential_diagnosis.domain.entities import DifferentialDiagnosis
from app.modules.differential_diagnosis.domain.enums import ReviewStatus
from app.modules.differential_diagnosis.domain.repositories import (
    DifferentialDiagnosisRepository,
)

_NOT_EDITABLE_STATUSES = frozenset({ReviewStatus.APPROVED, ReviewStatus.REJECTED})


class DifferentialDiagnosisQueryService:
    def __init__(
        self, *, differential_diagnosis_repository: DifferentialDiagnosisRepository
    ) -> None:
        self._diagnoses = differential_diagnosis_repository

    async def differential_diagnosis_exists(self, differential_diagnosis_id: UUID) -> bool:
        return await self._diagnoses.get_by_id(differential_diagnosis_id) is not None

    async def is_editable(self, differential_diagnosis_id: UUID) -> bool:
        diagnosis = await self._diagnoses.get_by_id(differential_diagnosis_id)
        return diagnosis is not None and diagnosis.review_status not in _NOT_EDITABLE_STATUSES

    async def get_differential_diagnosis_summary(
        self, differential_diagnosis_id: UUID
    ) -> DifferentialDiagnosisSummaryDTO | None:
        diagnosis = await self._diagnoses.get_by_id(differential_diagnosis_id)
        return _to_summary(diagnosis) if diagnosis is not None else None

    async def list_differential_diagnoses_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[DifferentialDiagnosisSummaryDTO]:
        diagnoses = await self._diagnoses.list_by_clinical_note(clinical_note_id)
        return [_to_summary(diagnosis) for diagnosis in diagnoses]

    async def list_differential_diagnoses_for_patient(
        self, patient_id: UUID
    ) -> list[DifferentialDiagnosisSummaryDTO]:
        diagnoses = await self._diagnoses.list_by_patient(patient_id)
        return [_to_summary(diagnosis) for diagnosis in diagnoses]


def _to_summary(diagnosis: DifferentialDiagnosis) -> DifferentialDiagnosisSummaryDTO:
    return DifferentialDiagnosisSummaryDTO(
        differential_diagnosis_id=diagnosis.id,
        organization_id=diagnosis.organization_id,
        clinical_note_id=diagnosis.clinical_note_id,
        patient_id=diagnosis.patient_id,
        visit_id=diagnosis.visit_id,
        doctor_id=diagnosis.doctor_id,
        diagnosis_name=diagnosis.diagnosis_name,
        diagnosis_source=diagnosis.diagnosis_source,
        ranking=diagnosis.ranking,
        review_status=diagnosis.review_status,
        excluded=diagnosis.excluded,
        clinical_reasoning_id=diagnosis.clinical_reasoning_id,
        likelihood_score=diagnosis.likelihood_score,
        supporting_evidence=diagnosis.supporting_evidence,
    )
