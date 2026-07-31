"""`PatientFacade` — the one concrete implementation of `PatientQueryPort`.
Constructed per-request by
`app.modules.patient.container.build_patient_facade`, bound to that
request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.patient.application.services.patient_query_service import PatientQueryService
from app.modules.patient.application.services.patient_sub_resource_query_service import (
    PatientAllergyQueryService,
    PatientMedicalConditionQueryService,
)
from app.modules.patient.public.dto import (
    PatientAllergySummaryDTO,
    PatientMedicalConditionSummaryDTO,
    PatientSummaryDTO,
)
from app.modules.patient.public.interfaces import PatientQueryPort


class PatientFacade(PatientQueryPort):
    def __init__(
        self,
        *,
        query_service: PatientQueryService,
        allergy_query_service: PatientAllergyQueryService,
        medical_condition_query_service: PatientMedicalConditionQueryService,
    ) -> None:
        self._query_service = query_service
        self._allergies = allergy_query_service
        self._conditions = medical_condition_query_service

    async def patient_exists(self, patient_id: UUID) -> bool:
        return await self._query_service.patient_exists(patient_id)

    async def is_active(self, patient_id: UUID) -> bool:
        return await self._query_service.is_active(patient_id)

    async def get_patient_summary(self, patient_id: UUID) -> PatientSummaryDTO | None:
        return await self._query_service.get_patient_summary(patient_id)

    async def list_allergies_for_patient(self, patient_id: UUID) -> list[PatientAllergySummaryDTO]:
        return await self._allergies.list_allergies_for_patient(patient_id)

    async def list_medical_conditions_for_patient(
        self, patient_id: UUID
    ) -> list[PatientMedicalConditionSummaryDTO]:
        return await self._conditions.list_conditions_for_patient(patient_id)
