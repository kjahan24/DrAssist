"""Read-only queries against `LabResult`/`LabResultItem`.

Backs the module's public `LabResultQueryPort` — the one implementation,
per `docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

Shaped like `app.modules.prescriptions.application.services
.prescription_query_service.PrescriptionQueryService`, not
`app.modules.lab_orders.application.services.lab_order_query_service
.LabOrderQueryService`: `LabResult` is one-to-*one* with `LabOrder` ("One
Lab Order may have at most one Lab Result"), so a single
`get_lab_result_summary(lab_order_id)` — not a `list_...` — is the query
keyed by the parent. `is_editable` mirrors `PrescriptionQueryService`'s
own reasoning: absent from the shared query API today (nothing in *this*
module needs it), but exposed publicly since a future consumer (AI Lab
Interpretation, in particular) needs to ask "can I still attach an
interpretation here?" without importing `LabResultStatus` across the
module boundary.

Depends on both repositories (like `PrescriptionQueryService`) because
`LabResultSummaryDTO` embeds the full item list — this task's own Future
Compatibility list (AI Lab Interpretation, Clinical Reasoning,
Differential Diagnosis, ICD-10 Coding, FHIR DiagnosticReport, HL7 ORU
Messages, LIS, Patient Timeline) all need the actual result data, not
just "a result exists".
"""

from uuid import UUID

from app.modules.lab_results.application.dto import LabResultItemSummaryDTO, LabResultSummaryDTO
from app.modules.lab_results.domain.entities import LabResult, LabResultItem
from app.modules.lab_results.domain.enums import LabResultStatus
from app.modules.lab_results.domain.repositories import (
    LabResultItemRepository,
    LabResultRepository,
)

_NOT_EDITABLE_STATUSES = frozenset({LabResultStatus.FINAL})


class LabResultQueryService:
    def __init__(
        self,
        *,
        lab_result_repository: LabResultRepository,
        lab_result_item_repository: LabResultItemRepository,
    ) -> None:
        self._lab_results = lab_result_repository
        self._items = lab_result_item_repository

    async def lab_result_exists_for_lab_order(self, lab_order_id: UUID) -> bool:
        return await self._lab_results.get_by_lab_order_id(lab_order_id) is not None

    async def is_editable(self, lab_order_id: UUID) -> bool:
        lab_result = await self._lab_results.get_by_lab_order_id(lab_order_id)
        return lab_result is not None and lab_result.status not in _NOT_EDITABLE_STATUSES

    async def get_lab_result_summary(self, lab_order_id: UUID) -> LabResultSummaryDTO | None:
        lab_result = await self._lab_results.get_by_lab_order_id(lab_order_id)
        if lab_result is None:
            return None
        return await self._to_summary(lab_result)

    async def get_lab_result_summary_by_id(self, lab_result_id: UUID) -> LabResultSummaryDTO | None:
        """By the lab result's own id — added by the REST APIs task so
        `AddLabResultItem` (whose output only carries `lab_result_id`, not
        `lab_order_id`) has a way to refetch the full summary after adding
        an item — see `PrescriptionQueryService.get_prescription_summary_by_id`
        for the identical situation."""
        lab_result = await self._lab_results.get_by_id(lab_result_id)
        if lab_result is None:
            return None
        return await self._to_summary(lab_result)

    async def list_lab_results_for_patient(self, patient_id: UUID) -> list[LabResultSummaryDTO]:
        lab_results = await self._lab_results.list_by_patient(patient_id)
        return [await self._to_summary(lab_result) for lab_result in lab_results]

    async def _to_summary(self, lab_result: LabResult) -> LabResultSummaryDTO:
        items = await self._items.list_by_lab_result(lab_result.id)
        return LabResultSummaryDTO(
            lab_result_id=lab_result.id,
            organization_id=lab_result.organization_id,
            lab_order_id=lab_result.lab_order_id,
            patient_id=lab_result.patient_id,
            visit_id=lab_result.visit_id,
            doctor_id=lab_result.doctor_id,
            result_number=lab_result.result_number,
            reported_at=lab_result.reported_at,
            status=lab_result.status,
            laboratory_name=lab_result.laboratory_name,
            comments=lab_result.comments,
            items=[_to_item_summary(item) for item in items],
        )


def _to_item_summary(item: LabResultItem) -> LabResultItemSummaryDTO:
    return LabResultItemSummaryDTO(
        lab_result_item_id=item.id,
        lab_result_id=item.lab_result_id,
        lab_order_item_id=item.lab_order_item_id,
        test_code=item.test_code,
        test_name=item.test_name,
        result_value=item.result_value,
        abnormal_flag=item.abnormal_flag,
        result_unit=item.result_unit,
        reference_range=item.reference_range,
        interpretation=item.interpretation,
    )
