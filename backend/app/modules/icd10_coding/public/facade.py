"""`ICD10CodingFacade` — the one concrete implementation of
`ICD10CodingQueryPort`. Constructed per-request by
`app.modules.icd10_coding.container.build_icd10_coding_facade`, bound to
that request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.icd10_coding.application.services.icd10_coding_query_service import (
    ICD10CodingQueryService,
)
from app.modules.icd10_coding.public.dto import ICD10CodingSummaryDTO
from app.modules.icd10_coding.public.interfaces import ICD10CodingQueryPort


class ICD10CodingFacade(ICD10CodingQueryPort):
    def __init__(self, *, query_service: ICD10CodingQueryService) -> None:
        self._query_service = query_service

    async def icd10_coding_exists(self, icd10_coding_id: UUID) -> bool:
        return await self._query_service.icd10_coding_exists(icd10_coding_id)

    async def is_editable(self, icd10_coding_id: UUID) -> bool:
        return await self._query_service.is_editable(icd10_coding_id)

    async def get_icd10_coding_summary(self, icd10_coding_id: UUID) -> ICD10CodingSummaryDTO | None:
        return await self._query_service.get_icd10_coding_summary(icd10_coding_id)

    async def get_primary_icd10_coding_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> ICD10CodingSummaryDTO | None:
        return await self._query_service.get_primary_icd10_coding_for_clinical_note(
            clinical_note_id
        )

    async def list_icd10_codings_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[ICD10CodingSummaryDTO]:
        return await self._query_service.list_icd10_codings_for_clinical_note(clinical_note_id)

    async def list_icd10_codings_for_patient(self, patient_id: UUID) -> list[ICD10CodingSummaryDTO]:
        return await self._query_service.list_icd10_codings_for_patient(patient_id)
