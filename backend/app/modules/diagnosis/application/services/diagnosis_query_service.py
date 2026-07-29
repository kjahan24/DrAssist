"""Read-only queries against `VisitDiagnosis`.

Backs the module's public `DiagnosisQueryPort` — the one implementation,
per `docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).
"""

from uuid import UUID

from app.modules.diagnosis.application.dto import DiagnosisSummaryDTO
from app.modules.diagnosis.domain.repositories import VisitDiagnosisRepository


class VisitDiagnosisQueryService:
    def __init__(self, *, diagnosis_repository: VisitDiagnosisRepository) -> None:
        self._diagnoses = diagnosis_repository

    async def diagnosis_exists(self, diagnosis_id: UUID) -> bool:
        return await self._diagnoses.get_by_id(diagnosis_id) is not None

    async def list_diagnoses_for_visit(self, visit_id: UUID) -> list[DiagnosisSummaryDTO]:
        diagnoses = await self._diagnoses.list_by_visit(visit_id)
        return [
            DiagnosisSummaryDTO(
                diagnosis_id=diagnosis.id,
                organization_id=diagnosis.organization_id,
                visit_id=diagnosis.visit_id,
                sequence_number=diagnosis.sequence_number,
                diagnosis_name=diagnosis.diagnosis_name,
                diagnosis_type=diagnosis.diagnosis_type,
                diagnosis_status=diagnosis.diagnosis_status,
            )
            for diagnosis in diagnoses
        ]
