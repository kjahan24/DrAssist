"""Read-only queries against `VisitVitalSigns`.

Backs the module's public `VitalSignsQueryPort` — the one implementation,
per `docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

`VitalSignsSummaryDTO`'s extra fields were added by the REST APIs task —
see `app.modules.diagnosis.application.services.diagnosis_query_service`'s
own docstring for the identical reasoning.
"""

from uuid import UUID

from app.modules.vital_signs.application.dto import VitalSignsSummaryDTO
from app.modules.vital_signs.domain.entities import VisitVitalSigns
from app.modules.vital_signs.domain.repositories import VisitVitalSignsRepository


class VisitVitalSignsQueryService:
    def __init__(self, *, vital_signs_repository: VisitVitalSignsRepository) -> None:
        self._vital_signs = vital_signs_repository

    async def vital_signs_exist_for_visit(self, visit_id: UUID) -> bool:
        return await self._vital_signs.get_by_visit_id(visit_id) is not None

    async def get_vital_signs_summary_for_visit(
        self, visit_id: UUID
    ) -> VitalSignsSummaryDTO | None:
        vital_signs = await self._vital_signs.get_by_visit_id(visit_id)
        return _to_summary(vital_signs) if vital_signs is not None else None


def _to_summary(vital_signs: VisitVitalSigns) -> VitalSignsSummaryDTO:
    return VitalSignsSummaryDTO(
        vital_signs_id=vital_signs.id,
        organization_id=vital_signs.organization_id,
        visit_id=vital_signs.visit_id,
        recorded_at=vital_signs.recorded_at,
        bmi=vital_signs.bmi,
        temperature_c=vital_signs.temperature_c,
        pulse_bpm=vital_signs.pulse_bpm,
        respiratory_rate=vital_signs.respiratory_rate,
        systolic_bp=vital_signs.blood_pressure.systolic,
        diastolic_bp=vital_signs.blood_pressure.diastolic,
        spo2=vital_signs.spo2,
        recorded_by=vital_signs.recorded_by,
        height_cm=vital_signs.height_cm,
        weight_kg=vital_signs.weight_kg,
        blood_glucose=vital_signs.blood_glucose,
        pain_score=vital_signs.pain_score,
    )
