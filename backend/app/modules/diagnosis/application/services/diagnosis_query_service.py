"""Read-only queries against `VisitDiagnosis`.

Backs the module's public `DiagnosisQueryPort` — the one implementation,
per `docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

`get_diagnosis_summary`/`DiagnosisSummaryDTO`'s extra fields were added
by the REST APIs task: this service previously had no "fetch one by its
own id" method (only `diagnosis_exists` — a bool — and
`list_diagnoses_for_visit`), but the "GetById" REST convention that task
implements needs one, and `api/schemas.py`'s own `VisitDiagnosisResponse`
(built in this module's original task, before endpoints existed) already
expected the fuller shape — this brings the query service in line with
the response shape that was always the intended target.
"""

from uuid import UUID

from app.modules.diagnosis.application.dto import DiagnosisSummaryDTO
from app.modules.diagnosis.domain.entities import VisitDiagnosis
from app.modules.diagnosis.domain.repositories import VisitDiagnosisRepository


class VisitDiagnosisQueryService:
    def __init__(self, *, diagnosis_repository: VisitDiagnosisRepository) -> None:
        self._diagnoses = diagnosis_repository

    async def diagnosis_exists(self, diagnosis_id: UUID) -> bool:
        return await self._diagnoses.get_by_id(diagnosis_id) is not None

    async def get_diagnosis_summary(self, diagnosis_id: UUID) -> DiagnosisSummaryDTO | None:
        diagnosis = await self._diagnoses.get_by_id(diagnosis_id)
        return _to_summary(diagnosis) if diagnosis is not None else None

    async def list_diagnoses_for_visit(self, visit_id: UUID) -> list[DiagnosisSummaryDTO]:
        diagnoses = await self._diagnoses.list_by_visit(visit_id)
        return [_to_summary(diagnosis) for diagnosis in diagnoses]


def _to_summary(diagnosis: VisitDiagnosis) -> DiagnosisSummaryDTO:
    return DiagnosisSummaryDTO(
        diagnosis_id=diagnosis.id,
        organization_id=diagnosis.organization_id,
        visit_id=diagnosis.visit_id,
        sequence_number=diagnosis.sequence_number,
        diagnosis_name=diagnosis.diagnosis_name,
        diagnosis_type=diagnosis.diagnosis_type,
        diagnosis_status=diagnosis.diagnosis_status,
        icd10_code=diagnosis.icd10_code,
        clinical_notes=diagnosis.clinical_notes,
        diagnosed_by=diagnosis.diagnosed_by,
        diagnosed_at=diagnosis.diagnosed_at,
    )
