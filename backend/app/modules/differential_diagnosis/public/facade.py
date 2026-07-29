"""`DifferentialDiagnosisFacade` — the one concrete implementation of
`DifferentialDiagnosisQueryPort`. Constructed per-request by
`app.modules.differential_diagnosis.container
.build_differential_diagnosis_facade`, bound to that request's
`AsyncSession`.
"""

from uuid import UUID

from app.modules.differential_diagnosis.application.services.differential_diagnosis_query_service import (  # noqa: E501
    DifferentialDiagnosisQueryService,
)
from app.modules.differential_diagnosis.public.dto import DifferentialDiagnosisSummaryDTO
from app.modules.differential_diagnosis.public.interfaces import DifferentialDiagnosisQueryPort


class DifferentialDiagnosisFacade(DifferentialDiagnosisQueryPort):
    def __init__(self, *, query_service: DifferentialDiagnosisQueryService) -> None:
        self._query_service = query_service

    async def differential_diagnosis_exists(self, differential_diagnosis_id: UUID) -> bool:
        return await self._query_service.differential_diagnosis_exists(differential_diagnosis_id)

    async def is_editable(self, differential_diagnosis_id: UUID) -> bool:
        return await self._query_service.is_editable(differential_diagnosis_id)

    async def get_differential_diagnosis_summary(
        self, differential_diagnosis_id: UUID
    ) -> DifferentialDiagnosisSummaryDTO | None:
        return await self._query_service.get_differential_diagnosis_summary(
            differential_diagnosis_id
        )

    async def list_differential_diagnoses_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[DifferentialDiagnosisSummaryDTO]:
        return await self._query_service.list_differential_diagnoses_for_clinical_note(
            clinical_note_id
        )

    async def list_differential_diagnoses_for_patient(
        self, patient_id: UUID
    ) -> list[DifferentialDiagnosisSummaryDTO]:
        return await self._query_service.list_differential_diagnoses_for_patient(patient_id)
