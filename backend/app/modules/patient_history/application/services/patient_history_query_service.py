"""Read-only queries against `PatientHistory`.

Backs the module's public `PatientHistoryQueryPort` — the one
implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

There is no `is_editable` here, unlike every prior module's query
service: "History records are immutable" is an unconditional fact about
every row, not a state a specific record can be in or out of — a method
that always returns `False` would be dead code (see
`domain/entities.py`).

`list_patient_history_for_patient` is ordered by `encounter_date` —
this is the query the stated Future Compatibility consumers (Timeline
View, Longitudinal EMR, FHIR Bundle, Patient Portal, Mobile App) all need
first: a patient's approved clinical history in chronological order.
`get_by_reference` exists for the same duplicate-prevention check
`application/use_cases/create_patient_history.py` performs, and doubles
as the lookup a future FHIR resource mapper would use to find "the
`PatientHistory` row for this source record."
"""

from uuid import UUID

from app.modules.patient_history.application.dto import PatientHistorySummaryDTO
from app.modules.patient_history.domain.entities import PatientHistory
from app.modules.patient_history.domain.enums import ReferenceType
from app.modules.patient_history.domain.repositories import PatientHistoryRepository


class PatientHistoryQueryService:
    def __init__(self, *, patient_history_repository: PatientHistoryRepository) -> None:
        self._history = patient_history_repository

    async def patient_history_exists(self, patient_history_id: UUID) -> bool:
        return await self._history.get_by_id(patient_history_id) is not None

    async def get_patient_history_summary(
        self, patient_history_id: UUID
    ) -> PatientHistorySummaryDTO | None:
        history = await self._history.get_by_id(patient_history_id)
        return _to_summary(history) if history is not None else None

    async def get_by_reference(
        self, reference_type: ReferenceType, reference_id: UUID
    ) -> PatientHistorySummaryDTO | None:
        history = await self._history.get_by_reference(reference_type, reference_id)
        return _to_summary(history) if history is not None else None

    async def list_patient_history_for_patient(
        self, patient_id: UUID
    ) -> list[PatientHistorySummaryDTO]:
        history = await self._history.list_by_patient(patient_id)
        return [_to_summary(item) for item in history]

    async def list_patient_history_for_visit(
        self, visit_id: UUID
    ) -> list[PatientHistorySummaryDTO]:
        history = await self._history.list_by_visit(visit_id)
        return [_to_summary(item) for item in history]


def _to_summary(history: PatientHistory) -> PatientHistorySummaryDTO:
    return PatientHistorySummaryDTO(
        patient_history_id=history.id,
        organization_id=history.organization_id,
        patient_id=history.patient_id,
        visit_id=history.visit_id,
        doctor_review_id=history.doctor_review_id,
        history_type=history.history_type,
        reference_type=history.reference_type,
        reference_id=history.reference_id,
        encounter_date=history.encounter_date,
        summary=history.summary,
        created_from_review=history.created_from_review,
    )
