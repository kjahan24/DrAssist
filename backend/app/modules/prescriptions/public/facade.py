"""`PrescriptionFacade` — the one concrete implementation of
`PrescriptionQueryPort`. Constructed per-request by
`app.modules.prescriptions.container.build_prescription_facade`, bound to
that request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.prescriptions.application.services.prescription_query_service import (
    PrescriptionQueryService,
)
from app.modules.prescriptions.public.dto import PrescriptionSummaryDTO
from app.modules.prescriptions.public.interfaces import PrescriptionQueryPort


class PrescriptionFacade(PrescriptionQueryPort):
    def __init__(self, *, query_service: PrescriptionQueryService) -> None:
        self._query_service = query_service

    async def prescription_exists_for_clinical_note(self, clinical_note_id: UUID) -> bool:
        return await self._query_service.prescription_exists_for_clinical_note(clinical_note_id)

    async def get_prescription_summary(
        self, clinical_note_id: UUID
    ) -> PrescriptionSummaryDTO | None:
        return await self._query_service.get_prescription_summary(clinical_note_id)

    async def list_prescriptions_for_patient(
        self, patient_id: UUID
    ) -> list[PrescriptionSummaryDTO]:
        return await self._query_service.list_prescriptions_for_patient(patient_id)
