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

from collections.abc import Sequence
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from app.modules.patient_history.application.dto import PatientHistorySummaryDTO
from app.modules.patient_history.domain.entities import PatientHistory
from app.modules.patient_history.domain.enums import HistoryType, ReferenceType
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

    async def search_patient_history(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        history_types: Sequence[HistoryType] | None = None,
        reference_types: Sequence[ReferenceType] | None = None,
        patient_id: UUID | None = None,
        visit_id: UUID | None = None,
        doctor_review_id: UUID | None = None,
        reference_id: UUID | None = None,
        encounter_date_from: date | None = None,
        encounter_date_to: date | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "encounter_date",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[PatientHistorySummaryDTO], int]:
        """Search & Filtering module — see
        `PatientHistoryRepository.search`'s docstring for filter/sort/
        pagination semantics."""
        history, total = await self._history.search(
            organization_id=organization_id,
            query=query,
            history_types=history_types,
            reference_types=reference_types,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_review_id=doctor_review_id,
            reference_id=reference_id,
            encounter_date_from=encounter_date_from,
            encounter_date_to=encounter_date_to,
            created_from=created_from,
            created_to=created_to,
            updated_from=updated_from,
            updated_to=updated_to,
            include_deleted=include_deleted,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=offset,
            limit=limit,
        )
        return [_to_summary(item) for item in history], total


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
