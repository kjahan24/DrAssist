"""Read-only queries against `ICD10Coding`.

Backs the module's public `ICD10CodingQueryPort` — the one
implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

Shaped like `app.modules.differential_diagnosis.application.services
.differential_diagnosis_query_service.DifferentialDiagnosisQueryService`:
`ICD10Coding` is one-to-*many* with `ClinicalNote` ("One Clinical Note
may contain multiple ICD-10 codes"), so
`list_icd10_codings_for_clinical_note` — not a single
`get_..._summary(clinical_note_id)` — is the query keyed by the parent;
`get_icd10_coding_summary` is instead keyed by this aggregate's own id.
`get_primary_icd10_coding_for_clinical_note` exists specifically for
future Billing Engine/Insurance Claims/DRG Coding consumers, which need
the single principal code for a clinical note without re-deriving "which
one is primary" themselves. `is_editable` mirrors the same boolean-not-
enum shape used throughout this session, so a future module can ask "can
this code still be modified?" without importing `ReviewStatus` across the
module boundary. `list_icd10_codings_for_patient` exists for the same
reason `app.modules.clinical_notes.application.services
.clinical_note_query_service.ClinicalNoteQueryService
.list_clinical_notes_for_patient` does: so a future Medical Analytics
module can assemble a patient's full coding history without this module
needing to change.
"""

from uuid import UUID

from app.modules.icd10_coding.application.dto import ICD10CodingSummaryDTO
from app.modules.icd10_coding.domain.entities import ICD10Coding
from app.modules.icd10_coding.domain.enums import ReviewStatus
from app.modules.icd10_coding.domain.repositories import ICD10CodingRepository

_NOT_EDITABLE_STATUSES = frozenset({ReviewStatus.APPROVED, ReviewStatus.REJECTED})


class ICD10CodingQueryService:
    def __init__(self, *, icd10_coding_repository: ICD10CodingRepository) -> None:
        self._codings = icd10_coding_repository

    async def icd10_coding_exists(self, icd10_coding_id: UUID) -> bool:
        return await self._codings.get_by_id(icd10_coding_id) is not None

    async def is_editable(self, icd10_coding_id: UUID) -> bool:
        coding = await self._codings.get_by_id(icd10_coding_id)
        return coding is not None and coding.review_status not in _NOT_EDITABLE_STATUSES

    async def get_icd10_coding_summary(self, icd10_coding_id: UUID) -> ICD10CodingSummaryDTO | None:
        coding = await self._codings.get_by_id(icd10_coding_id)
        return _to_summary(coding) if coding is not None else None

    async def get_primary_icd10_coding_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> ICD10CodingSummaryDTO | None:
        coding = await self._codings.get_primary_for_clinical_note(clinical_note_id)
        return _to_summary(coding) if coding is not None else None

    async def list_icd10_codings_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[ICD10CodingSummaryDTO]:
        codings = await self._codings.list_by_clinical_note(clinical_note_id)
        return [_to_summary(coding) for coding in codings]

    async def list_icd10_codings_for_patient(self, patient_id: UUID) -> list[ICD10CodingSummaryDTO]:
        codings = await self._codings.list_by_patient(patient_id)
        return [_to_summary(coding) for coding in codings]


def _to_summary(coding: ICD10Coding) -> ICD10CodingSummaryDTO:
    return ICD10CodingSummaryDTO(
        icd10_coding_id=coding.id,
        organization_id=coding.organization_id,
        clinical_note_id=coding.clinical_note_id,
        patient_id=coding.patient_id,
        visit_id=coding.visit_id,
        doctor_id=coding.doctor_id,
        icd10_code=coding.icd10_code,
        diagnosis_title=coding.diagnosis_title,
        coding_source=coding.coding_source,
        primary_code=coding.primary_code,
        review_status=coding.review_status,
        differential_diagnosis_id=coding.differential_diagnosis_id,
        coding_notes=coding.coding_notes,
    )
