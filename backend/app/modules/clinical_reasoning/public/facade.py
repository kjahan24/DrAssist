"""`ClinicalReasoningFacade` — the one concrete implementation of
`ClinicalReasoningQueryPort`. Constructed per-request by
`app.modules.clinical_reasoning.container.build_clinical_reasoning_facade`,
bound to that request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.clinical_reasoning.application.services.clinical_reasoning_query_service import (
    ClinicalReasoningQueryService,
)
from app.modules.clinical_reasoning.public.dto import ClinicalReasoningSummaryDTO
from app.modules.clinical_reasoning.public.interfaces import ClinicalReasoningQueryPort


class ClinicalReasoningFacade(ClinicalReasoningQueryPort):
    def __init__(self, *, query_service: ClinicalReasoningQueryService) -> None:
        self._query_service = query_service

    async def clinical_reasoning_exists(self, clinical_reasoning_id: UUID) -> bool:
        return await self._query_service.clinical_reasoning_exists(clinical_reasoning_id)

    async def is_editable(self, clinical_reasoning_id: UUID) -> bool:
        return await self._query_service.is_editable(clinical_reasoning_id)

    async def get_clinical_reasoning_summary(
        self, clinical_reasoning_id: UUID
    ) -> ClinicalReasoningSummaryDTO | None:
        return await self._query_service.get_clinical_reasoning_summary(clinical_reasoning_id)

    async def list_clinical_reasoning_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[ClinicalReasoningSummaryDTO]:
        return await self._query_service.list_clinical_reasoning_for_clinical_note(clinical_note_id)

    async def list_clinical_reasoning_for_patient(
        self, patient_id: UUID
    ) -> list[ClinicalReasoningSummaryDTO]:
        return await self._query_service.list_clinical_reasoning_for_patient(patient_id)
